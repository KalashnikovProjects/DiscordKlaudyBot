import asyncio
import json
import logging
import random
import traceback
import aiohttp
import discord
import google.api_core.exceptions
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold
from mimetypes import guess_extension
from retry import retry

from . import config
from . import gpt_tools
from . import utils

genai.configure(api_key=config.Gemini.token,
                client_options={"api_endpoint": config.Gemini.server},
                transport=config.Gemini.transport)


def generate_function_call(name, args):
    return {
        "role": "model",
        "parts": [{
            "function_call": {
                "name": name,
                "args": args
            }
        }]
    }


# noinspection PyTypeChecker
def generate_function_response(name, function_response):
    return genai.protos.Content(parts=[genai.protos.Part(
        function_response=genai.protos.FunctionResponse(
            name=name,
            response={"response": function_response}))], role="function")
    # return {
    #     "role": "function",
    #     "parts": [{
    #         "function_response": {
    #             "name": name,
    #             "response": {"response": function_response}
    #         }
    #     }]
    # }


def stop_log(res):
    finish_reasons = {1: "баг в Клауди", 2: "лимит длинны запроса/ответа", 3: "тут был жесткий ответ, но гугл его не пропустил",
                      4: "повторяющиеся токены в запросе", 5: "баг на стороне гуглов", 6: "неподдерживаемый язык",
                      7: "в ответе были слова из чёрного списка гугла", 8: "в ответе Клауди цензура нашла запрещённый контент",
                      9: "Клауди хотел слить чьи-то личные данные, но цензура не пропустила",
                      10: "Клауди хотел вызвать функцию, но его запрос инвалид"}
    finish_reason = finish_reasons.get(res.candidates[0].finish_reason, f"неизвестная ошибка. finish_reason: {res.candidates[0].finish_reason}")
    logging.info(f"Ошибка при генерации ответа {finish_reason}, оценки безопасности {res.candidates[0].safety_ratings}")
    logging.debug(res)
    return f"Ошибка при генерации ответа `{finish_reason}`"


async def upload_file(data, content_type, filename):
    r = random.randint(0, 1000000000)
    num_bytes = len(data)

    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(num_bytes),
        "X-Goog-Upload-Header-Content-Type": content_type or "text/plain",
        "Content-Type": "application/json"
    }
    json_data = json.dumps({"file": {"display_name": f"{r}-{filename}.{guess_extension(content_type)}"}})

    async with aiohttp.ClientSession() as session:
        async with session.post(
                f"https://{config.Gemini.server}/upload/v1beta/files?key={config.Gemini.token}&alt=json&uploadType=resumable",
                headers=headers,
                data=json_data
        ) as response:
            upload_url = response.headers.get("Location")

        headers = {
            "Content-Length": str(num_bytes),
            "X-Goog-Upload-Offset": "0",
            "X-Goog-Upload-Command": "upload, finalize"
        }
        async with session.post(upload_url, headers=headers, data=data) as response:
            file_info = await response.json()

        file_uri = file_info["file"]["uri"]
        state = file_info["file"]["state"]

        logging.info("uploading file")
        if state == "ACTIVE":
            return file_uri
        while state == "PROCESSING":
            await asyncio.sleep(0.5)
            file = genai.get_file(file_info["file"]["name"])
            state = file.state.name
        if not file:
            raise ValueError(state)
        if file.state.name == "FAILED":
            raise ValueError(file.state.name)

    return file_uri


class GPT:
    def __init__(self, bot):
        self.voice_connections = {}
        self.bot: discord.Client = bot

        self.generation_config = genai.types.GenerationConfig(
            temperature=config.Gemini.temperature,
            max_output_tokens=config.Gemini.max_output_tokens,
            candidate_count=1)

        self.no_safety = {i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}
        # No censor, our bot toxic

        self.voice_tools = gpt_tools.VoiceTools()
        self.text_tools = gpt_tools.TextTools(gpt_obj=self)

    async def generate_answer_for_voice(self, wav_data, author, channel: discord.VoiceChannel, retries=1):
        try:
            additional_info = f"Информация о голосовом чате\nНазвание сервера: {channel.guild.name}\nНазвание голосового канала: {channel.name}\nСписок ников пользователей голосового чата: "
            if len(channel.members) < config.BotConfig.members_info_limit:
                for member in channel.members:
                    additional_info += f"{member.display_name}: {member.name}; "
            model = genai.GenerativeModel(
                model_name=config.Gemini.main_model,
                generation_config=self.generation_config,
                safety_settings=self.no_safety,
                system_instruction=f"{config.BotConfig.bot_prompt_voice}\n{additional_info}"
            )
            messages = [{"role": "user", "parts": [{"text": f"{author.display_name} (голосовое сообщение)"},
                                                   {"inline_data": {"data": wav_data, "mime_type": "audio/wav"}}]}, ]

            res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                          contents=messages,
                                          tools=gpt_tools.voice_tools)

            func_call = [i.function_call for i in res.candidates[0].content.parts if "function_call" in i]
            if not func_call:
                if retries:
                    return await self.generate_answer_for_voice(wav_data, author=author, channel=channel,
                                                                retries=retries - 1)
                return res.text
            else:
                tool_call = func_call[0]

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.voice_tools, tool_call.name, gpt_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools (ВОЙС): {tool_call.name}, {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))
                res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                              contents=messages, generation_config=self.generation_config)
                return res.text
        except google.api_core.exceptions.GoogleAPIError as e:
            if retries:
                logging.warning(e)
                return await self.generate_answer_for_voice(wav_data, author=author, channel=channel,
                                                            retries=retries - 1)
            logging.error(traceback.format_exc())
            return "Ошибка со стороны гугла"
        except Exception as e:
            if retries:
                logging.warning(e)
                return await self.generate_answer_for_voice(wav_data, author=author, channel=channel,
                                                            retries=retries - 1)
            logging.error(traceback.format_exc())
            return "Ошибка при генерации ответа"

    async def generate_answer(self, messages, mes=None, additional_info="", retries=1):
        try:
            model = genai.GenerativeModel(
                model_name=config.Gemini.main_model,
                generation_config=self.generation_config,
                safety_settings=self.no_safety,
                system_instruction=f"{config.BotConfig.bot_prompt}\n{additional_info}",
            )
            res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                          contents=messages,
                                          tools=gpt_tools.text_tools,
                                          generation_config=self.generation_config)
            if not res.parts:
                return stop_log(res)
            func_call = [i.function_call for i in res.candidates[0].content.parts if "function_call" in i]
            if not func_call:
                if retries:
                    return await self.generate_answer(messages, mes=mes, additional_info=additional_info,
                                                      retries=retries - 1)
                return res.text
            else:
                tools_logs = []
                tool_call = func_call[0]

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.text_tools, tool_call.name, gpt_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("enjoy_voice", "play_from_text", "stop_from_text", "get_que_from_text"):
                    func_kwargs["message"] = mes

                function_response = await function_to_call(**func_kwargs)

                if tool_call.name in ("search_gif_on_tenor", "play_from_text", "get_que_from_text"):
                    tools_logs.append(function_response)
                logging.info(f"tools: {tool_call.name}, {func_kwargs} {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))

                res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                              contents=messages, generation_config=self.generation_config)
                if not res.parts:
                    return stop_log(res)
                result_text = res.text
                print([result_text, ])
                for i in tools_logs:
                    result_text += f"{i}\n"
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            if retries:
                logging.warning(e)
                return await self.generate_answer(messages, mes=mes, additional_info=additional_info,
                                                  retries=retries - 1)
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            if retries:
                logging.warning(e)
                return await self.generate_answer(messages, mes=mes, additional_info=additional_info,
                                                  retries=retries - 1)
            logging.error(traceback.format_exc())
            return f"Ошибка {e}"

    # Decorator select token
    @retry(tries=1, delay=2)
    @utils.api_rate_limiter_with_ques(rate_limit=config.Gemini.main_rate_limit, tokens=config.Gemini.tokens)
    def generate_gemini_1_5_flesh(self, *args, model, token=config.Gemini.token, **kwargs):
        genai.configure(api_key=token,
                        client_options={"api_endpoint": config.Gemini.server},
                        transport=config.Gemini.transport)
        res = model.generate_content(*args, **kwargs)
        return res
