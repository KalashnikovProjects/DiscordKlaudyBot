import asyncio
import logging

import discord
import google.api_core.exceptions
import google.generativeai as genai
import openai
import google.ai.generativelanguage as glm

import traceback

from google.generativeai.types import HarmBlockThreshold

import config
import klaudy_tools
import utils


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


def generate_function_response(name, function_response):
    return glm.Content(parts=[glm.Part(
        function_response=glm.FunctionResponse(
            name=name,
            response={"response": function_response}))], role="function")
    # Хз почему только так работает
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
    finish_reasons = {1: "баг в Клауди", 2: "лимит длинны запроса/ответа", 3: "цензура блочит",
                      4: "повторяющиеся токены в запросе", 5: "баг на стороне гуглов"}
    logging.info(
        f"Ошибка при генерации ответа {finish_reasons[res.candidates[0].finish_reason]}, {res.candidates[0].safety_ratings}")
    logging.debug(res)
    return f"Ошибка при генерации ответа `{finish_reasons[res.candidates[0].finish_reason]}`"


class GPT:
    def __init__(self, bot):
        self.voice_connections = {}
        self.bot: discord.Client = bot

        self.openai_client = openai.AsyncOpenAI(
            api_key=config.openai_token,
            base_url=config.openai_server,
            max_retries=0,
            timeout=config.requests_timeout
        )

        no_safety = {i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}

        self.gemini_model = genai.GenerativeModel(
            model_name='models/gemini-1.0-pro',
            generation_config=genai.types.GenerationConfig(
                candidate_count=1),
            safety_settings=no_safety,
            # Отключаем цензуру, у нас бот токсик
        )
        self.gemini_image_model = genai.GenerativeModel(
            model_name='models/gemini-1.5-pro-latest',
            generation_config=genai.types.GenerationConfig(
                candidate_count=1),
            system_instruction=config.klaudy_knowns,
            safety_settings=no_safety,
            # Отключаем цензуру, у нас бот токсик
        )
        self.gemini_voice_model = genai.GenerativeModel(
            model_name='models/gemini-1.0-pro',
            generation_config=genai.types.GenerationConfig(
                candidate_count=1),
            safety_settings=no_safety,
            # Отключаем цензуру, у нас бот токсик
        )

        genai.configure(api_key=config.gemini_token,
                        client_options={"api_endpoint": config.gemini_server},
                        transport=config.gemini_transport, )

        self.voice_tools = klaudy_tools.VoiceTools()
        self.text_tools = klaudy_tools.TextTools(gpt_obj=self)

    async def generate_answer_in_voice(self, query, author, channel: discord.VoiceChannel, voice_history):
        info_message = f"""\n[СИСТЕМНАЯ ИНФОРМАЦИЯ] Информация о голосовом чате
                    Название сервера: {channel.guild.name}
                    Название голосового канала: {channel.name}"""
        if len(channel.members) < 12:
            info_message += f"\nСписок ников пользователей голосового чата чата: {', '.join([i.display_name for i in channel.members])}"
        messages = [{"role": "user", "parts": [{"text": f"{config.klaudy_knowns}\ninfo_message"}]},
                    *voice_history,
                    {"role": "user", "parts": [{"text": f"{author.display_name}: {query}"}]}]
        if messages[1]["role"] == "user":
            messages.insert(1, {"role": "model", "parts": [{"text": f"ок"}]})
        try:
            res = await asyncio.to_thread(self.gemini_voice_model.generate_content, contents=messages,
                                          tools=klaudy_tools.voice_tools,
                                          request_options={'timeout': 100, 'retry': google.api_core.retry.Retry()})
            if not res.parts:
                return stop_log(res)
            func_call = [i.function_call for i in res.candidates[0].content.parts if "function_call" in i]
            if not func_call:
                return res.text
            else:
                tool_call = func_call[0]

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.voice_tools, tool_call.name, klaudy_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools (ВОЙС): {tool_call.name}, {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))
                res = await asyncio.to_thread(self.gemini_voice_model.generate_content, contents=messages,
                                              request_options={'timeout': 100, 'retry': google.api_core.retry.Retry()})
                if not res.parts:
                    return stop_log(res)
                result_text = res.text
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка {e}"

    async def generate_answer(self, messages, images=False, members=None, mes=None):
        if members is None:
            members = {}
        try:
            if images:
                res = await asyncio.to_thread(self.generate_with_image, contents=messages,
                                              tools=klaudy_tools.text_tools,
                                              request_options={'timeout': 100,
                                                               'retry': google.api_core.retry.Retry()})
                # self.gemini_voice_model._system_instruction = google.generativeai.types.content_types.to_content(info)
            else:
                res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages,
                                              tools=klaudy_tools.text_tools,
                                              request_options={'timeout': 100, 'retry': google.api_core.retry.Retry()})
            if not res.parts:
                return stop_log(res)
            func_call = [i.function_call for i in res.candidates[0].content.parts if "function_call" in i]
            if not func_call:
                return res.text
            else:
                tools_logs = []
                tool_call = func_call[0]

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.text_tools, tool_call.name, klaudy_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name == "get_member":
                    func_kwargs["members"] = members
                if tool_call.name in ("enjoy_voice", "play_from_text", "stop_from_text", "get_que_from_text"):
                    func_kwargs["message"] = mes

                function_response = await function_to_call(**func_kwargs)

                if tool_call.name in ("search_gif_on_tenor", "play_from_text", "get_que_from_text"):
                    tools_logs.append(function_response)
                logging.info(f"tools: {tool_call.name}, {func_kwargs} {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))
                if images:
                    res = await asyncio.to_thread(self.generate_with_image, contents=messages,
                                                  request_options={'timeout': 100,
                                                                   'retry': google.api_core.retry.Retry()})
                else:
                    res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages,
                                                  request_options={'timeout': 100,
                                                                   'retry': google.api_core.retry.Retry()})
                if not res.parts:
                    return stop_log(res)
                result_text = res.text
                for i in tools_logs:
                    result_text += f"\n{i}"
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка {e}"

    @utils.api_rate_limiter_with_ques(rate_limit=config.tts_rate_limit, tokens=config.openai_tokens)
    async def generate_tts(self, *args, token, **kwargs):
        self.openai_client.api_key = token
        res = await self.openai_client.audio.speech.create(*args, **kwargs)
        return res

    @utils.api_rate_limiter_with_ques(rate_limit=config.gemini_15_rate_limit, tokens=config.gemini_tokens)
    def generate_with_image(self, *args, token, **kwargs):
        genai.configure(api_key=token,
                        client_options={"api_endpoint": config.gemini_server},
                        transport=config.gemini_transport, )

        res = self.gemini_image_model.generate_content(*args, **kwargs)
        return res
