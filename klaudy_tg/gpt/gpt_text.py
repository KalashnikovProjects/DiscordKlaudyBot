import json
import logging
import traceback
from typing import AsyncGenerator

import discord
from discord import Member
from mistralai import Mistral

from klaudy import config
from klaudy.gpt.tools import fake_tool
from klaudy.gpt.tools.text import TEXT_TOOLS_DEFINITION, TEXT_TOOLS_ENABLED_FOR_PM_DEFINITION, TextTools
from klaudy.audio.voice_connections import VoiceConnections


class TextGPT:
    def __init__(self):
        self.client = Mistral(api_key=config.Mistral.token)

        self.model = config.Mistral.main_model
        self.temperature = config.Mistral.temperature
        self.max_tokens = config.Mistral.max_output_tokens

        self.text_tools = TextTools()

    async def generate_answer_parts(
        self,
        messages_history: list[dict],
        voice_connections: VoiceConnections,
        bot_user_id: int,
        mes: discord.Message,
        members: dict[str, Member],
        additional_info="",
        retries=1,
        is_pm=False,
    ) -> AsyncGenerator[str]:
        try:
            messages = [{
                "role": "system",
                "content": f"{config.BotConfig.bot_prompt}\n{additional_info}"
            }]
            messages.extend(messages_history)

            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=1,
                tools=TEXT_TOOLS_DEFINITION if not is_pm else TEXT_TOOLS_ENABLED_FOR_PM_DEFINITION,
                tool_choice="auto",
                parallel_tool_calls=True,
            )
            tools_logs = []
            while response.choices[0].message.tool_calls:
                messages.append(response.choices[0].message)
                if response.choices[0].message.content:
                    res = response.choices[0].message.content
                    if tools_logs:
                        res += "\n" + "\n".join(tools_logs)
                        tools_logs = []
                    yield res

                for tool_call in response.choices[0].message.tool_calls:
                    function_name = tool_call.function.name
                    function_params = json.loads(tool_call.function.arguments)
                    function_to_call = getattr(
                        self.text_tools,
                        function_name,
                        fake_tool
                    )
                    if function_name == "send_personal_message":
                        function_params["message"] = mes
                        function_params["members"] = members


                    if function_name in ("stop_from_text", "get_que_from_text"):
                        function_params["message"] = mes
                        function_params["voice_connections"] = voice_connections

                    if function_name in ("enjoy_voice", "play_from_text"):
                        function_params["message"] = mes
                        function_params["voice_connections"] = voice_connections
                        function_params["bot_user_id"] = bot_user_id

                    function_response = await function_to_call(**function_params)
                    if function_name in ("play_from_text", "get_que_from_text"):
                        tools_logs.append(function_response)
                    print(f"Tool {tool_call.id}:", f"{function_name}({function_params}) -> {function_response}")

                    messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                        "tool_call_id": tool_call.id
                    })
                response = self.client.chat.complete(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    top_p=1,
                    tools=TEXT_TOOLS_DEFINITION,
                    tool_choice="auto",
                    parallel_tool_calls=True,
                )
            res = response.choices[0].message.content
            if tools_logs:
                res += "\n" + "\n".join(tools_logs)
                tools_logs = []
            yield res


        except Exception as e:
            logging.error(traceback.format_exc())
            if retries:
                async for i in self.generate_answer_parts(
                    messages_history,
                    voice_connections,
                    bot_user_id,
                    mes,
                    members,
                    additional_info,
                    retries - 1
                ):
                    yield i
            yield f"Ошибка Mistral: {e}"
