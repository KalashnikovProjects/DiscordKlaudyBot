import asyncio
import contextlib
import logging
from typing import Callable

from google import genai

from google.genai.types import LiveConnectConfig, Modality, GenerationConfig, \
    FunctionResponse, ContextWindowCompressionConfig, SlidingWindow, Blob, LiveServerMessage, SpeechConfig, VoiceConfig, \
    PrebuiltVoiceConfig, Tool, FunctionDeclaration
from klaudy import config
from klaudy.gpt.tools.voice import VOICE_TOOLS_DEFINITION, VoiceTools
from klaudy.gpt.tools import fake_tool
from klaudy.audio import mixer


class VoiceGPTClient:
    def __init__(self, mixer_player: mixer.PCMMixer, output_callback: Callable[[bytes], None], additional_info=""):
        self._session_task = None
        self._stop_event = None
        self.output_callback: Callable[[bytes], None] = output_callback
        self.generation_config = GenerationConfig(
            temperature=config.Gemini.temperature,
            max_output_tokens=config.Gemini.max_output_tokens,
            candidate_count=1)
        self.voice_tools = VoiceTools()
        self.mixer_player = mixer_player
        self.loop = asyncio.get_running_loop()

        self.client = genai.Client(api_key=config.Gemini.token)
        self.gemini_config = LiveConnectConfig(
            response_modalities=[Modality.AUDIO],
            context_window_compression=(
                ContextWindowCompressionConfig(
                    sliding_window=SlidingWindow(),
                )
            ),
            speech_config=SpeechConfig(
                language_code="ru-RU",
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(
                        voice_name="Sadachbia"
                    )
                )
            ),
            tools=[Tool(function_declarations=[
                FunctionDeclaration(
                    name=i["name"],
                    description=i["description"],
                    behavior=i.get("behavior"),
                    parameters=i["parameters"],
                )
            ]) for i in VOICE_TOOLS_DEFINITION],
            system_instruction=f"{config.BotConfig.bot_prompt_voice}\n{additional_info}",
            generation_config=self.generation_config,
        )
        self.session = None
        self.state = "initialization"
        self.que: list[bytes] = []


    @classmethod
    async def new_session(cls, mixer_player: mixer.PCMMixer, output_callback: Callable[[bytes], None], additional_info="") -> 'VoiceGPTClient':
        instance = cls(mixer_player, output_callback, additional_info=additional_info)
        await instance.start_session()
        return instance

    async def start_session(self):
        if self._session_task is not None:
            return

        self._stop_event = asyncio.Event()
        self._session_task = asyncio.create_task(self._session_runner())

    async def _session_runner(self):
        async with self.client.aio.live.connect(
                model=config.Gemini.voice_model,
                config=self.gemini_config,
        ) as session:
            self.session = session
            self.state = "running"
            await self.boom_que_after_init()

            receive_task = asyncio.create_task(self.receive_loop())

            await self._stop_event.wait()

            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task

        self.state = "closed"
        self.session = None

    async def receive_loop(self):
        while True:
            async for response in self.session.receive():
                try:
                    await self._process_response(response)
                except Exception as e:
                    logging.error(f"Unexpected error: {e}")
            await asyncio.sleep(0.01)

    async def _process_response(self, response: LiveServerMessage):
        if response.data is not None:
            self.output_callback(response.data)
        elif response.tool_call:
            for call in response.tool_call.function_calls:
                function_to_call = getattr(self.voice_tools, call.name, fake_tool)

                func_kwargs = {i: call.args[i] for i in call.args}
                if call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools: {call.name}, {func_kwargs} {function_response}")
                function_response = FunctionResponse(
                    name=call.name,
                    response=function_response,
                    id=call.id,
                )
                await self.session.send_tool_response(
                    function_responses=function_response
                )
        else:
            logging.warning(f"strange receive {response.dict()}")

    async def boom_que_after_init(self):
        for i in self.que:
            await self.session.send_realtime_input(
                audio=Blob(data=i, mime_type="audio/pcm;rate=16000")
            )
        self.que = []

    async def send(self, audio_bytes: bytes):
        if self.state == "closed":
            logging.warning("sending to the closed voice gpt client session")
            return
        if self.state == "initialization":
            self.que.append(audio_bytes)
            return
        await self.session.send_realtime_input(
            audio=Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
        )


    async def disconnect(self):
        self._stop_event.set()
        await self._session_task
        self._session_task = None
        self.state = "closed"
