import asyncio
import logging
import time

import discord
import google.api_core.exceptions
import google.generativeai as genai
import openai
from google.generativeai.types import HarmBlockThreshold
import google.ai.generativelanguage as glm

import traceback

import config
import klaudy_tools
import utils


class QueTimoutError(Exception):
    pass


def generate_function_call(name, args):
    # messages.append(
    #     {
    #         "role": "model",
    #         "parts": [{
    #             "functionCall": {
    #                 "name": tool_call.name,
    #                 "args": args
    #             }
    #         }]
    #     }
    # )
    # На данный момент API Gemini находится в бете, и функции из за бага принимает только так
    return glm.Content(parts=[glm.Part(
                    function_call=glm.FunctionCall(
                        name=name,
                        args=args))], role="model")


def generate_function_response(name, function_response):
    # messages.append(
    #     {
    #         "role": "function",
    #         "parts": [{
    #             "functionResponse": {
    #                 "name": tool_call.name,
    #                 "response": {"response": function_response}
    #             }
    #         }]
    #     }
    # )
    # На данный момент API Gemini находится в бете, и функции из за бага принимает только так
    return glm.Content(parts=[glm.Part(
                       function_response=glm.FunctionResponse(
                        name=name,
                        response={"response": function_response}))], role="function")


def stop_log(res):
    finish_reasons = {1: "баг в Клауди", 2: "лимит длинны запроса/ответа", 3: "цензура блочит", 4: "повторяющиеся токены в запросе", 5: "баг на стороне гуглов"}
    logging.info(f"Ошибка при генерации ответа {finish_reasons[res.candidates[0].finish_reason]}, {res.candidates[0].safety_ratings}")
    logging.debug(res)
    return f"Ошибка при генерации ответа `{finish_reasons[res.candidates[0].finish_reason]}`"


class GPT:
    def __init__(self, bot):
        self.tts_que = [[] for _ in range(len(config.openai_tokens))]
        self.tts_count = [3 for _ in range(len(config.openai_tokens))]
        self.voice_connections = {}
        self.bot: discord.Client = bot

        self.openai_client = openai.AsyncOpenAI(
            api_key=config.openai_token,
            base_url=config.openai_server,
            max_retries=0,
            timeout=config.openai_timeout
        )

        self.gemini_model = genai.GenerativeModel(
            model_name='models/gemini-1.0-pro',
            generation_config=genai.types.GenerationConfig(
                candidate_count=1),
            safety_settings={i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}
            # Отключаем цензуру, у нас бот токсик
        )
        self.gemini_image_model = genai.GenerativeModel(
            model_name='models/gemini-pro-vision',
            generation_config=genai.types.GenerationConfig(
                candidate_count=1),
            safety_settings={i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}
            # Отключаем цензуру, у нас бот токсик
        )
        self.voice_tools = klaudy_tools.VoiceTools()
        self.text_tools = klaudy_tools.TextTools(gpt_obj=self)

    async def generate_answer_in_voice(self, query, author, channel: discord.VoiceChannel, voice_history):
        info_message = f"""[СИСТЕМНАЯ ИНФОРМАЦИЯ] Информация о голосовом чате
                    Название сервера: {channel.guild.name}
                    Название голосового канала: {channel.name}"""
        if len(channel.members) < 12:
            info_message += f"\nСписок ников пользователей голосового чата чата: {', '.join([i.display_name for i in channel.members])}"
        messages = [{"role": "user", "parts": [{"text": f"{config.klaudy_knowns}\ninfo_message"}]},
                    *voice_history,
                    {"role": "user", "parts": [{"text": f"{author.display_name}: {query}"}]}]
        if messages[1]["role"] == "user":
            messages.insert(1, {"role": "model", "parts": [{"text": f"ок"}]}, )
        try:
            res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages,
                                          tools=klaudy_tools.voice_tools)
            if not res.parts:
                return stop_log(res)
            if 'function_call' not in res.candidates[0].content.parts[0]:
                return res.text
            else:
                tool_call = res.candidates[0].content.parts[0].function_call

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.voice_tools, tool_call.name, klaudy_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools (ВОЙС): {tool_call.name}, {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))
                res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages)
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

    async def generate_image_answer(self, messages):
        try:
            res = self.gemini_image_model.generate_content(
                contents=messages,
            )
            if not res.parts:
                return stop_log(res)
            return res.text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка: {e}"

    async def generate_answer(self, messages, members=None, mes=None):
        if members is None:
            members = {}
        try:
            res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages, tools=klaudy_tools.text_tools)
            if not res.parts:
                return stop_log(res)
            if 'function_call' not in res.candidates[0].content.parts[0]:
                return res.text
            else:
                tools_logs = []
                tool_call = res.candidates[0].content.parts[0].function_call

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
                res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages)
                if not res.parts:
                    return stop_log(res)
                result_text = res.text
                for i in tools_logs:
                    result_text += f"\n`{i}`"
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка {e}"

    async def que_tts(self, **kwargs):
        my_num, _ = max(enumerate(self.tts_count), key=lambda x: x[1])
        if self.tts_que[my_num] or self.tts_count[my_num] <= 0:
            my = time.time()
            my_num, my_que = min(enumerate(self.tts_que), key=lambda x: len(x[1]))
            my_que.append(my)
            while my in self.tts_que[my_num]:
                await asyncio.sleep(1)
                if time.time() - my > config.que_timeout:
                    my_que.pop(my_que.index(my))
                    raise QueTimoutError()
        self.tts_count[my_num] -= 1
        self.openai_client.api_key = config.openai_tokens[my_num]
        res = await self.openai_client.audio.speech.create(**kwargs)
        utils.run_in_thread(self.tts_timer_reset(my_num))
        return res

    async def tts_timer_reset(self, my_num):
        await asyncio.sleep(60)
        if self.tts_count[my_num] != len(config.openai_tokens) * 3:
            self.tts_count[my_num] += 1

    async def tts_que_progress(self):
        while True:
            for i in range(len(self.tts_que)):
                sleep_count = min(len(self.tts_que[i]), self.tts_count[i])
                for _ in range(sleep_count):
                    self.tts_que[i].pop(0)
                    await asyncio.sleep(1)
            await asyncio.sleep(0.1)
