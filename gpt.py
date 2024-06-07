import asyncio
import itertools
import logging

import discord
import google.api_core.exceptions
import google.generativeai as genai
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


# noinspection PyTypeChecker
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

        self.generation_config = google.generativeai.GenerationConfig(temperature=config.Gemini.temperature,
                                                                      max_output_tokens=config.Gemini.max_output_tokens,)

        self.no_safety = {i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}
        # Отключаем цензуру, у нас бот токсик

        self.voice_tools = klaudy_tools.VoiceTools()
        self.text_tools = klaudy_tools.TextTools(gpt_obj=self)

    async def generate_stream_answer_fom_voice(self, wav_data, author, channel: discord.VoiceChannel):
        try:
            additional_info = f"Информация о голосовом чате\nНазвание сервера: {channel.guild.name}\nНазвание голосового канала: {channel.name}\nСписок ников пользователей голосового чата: "
            if len(channel.members) < config.BotConfig.members_info_limit:
                for member in channel.members:
                    additional_info += f"{member.display_name}: {member.name}; "
            model = genai.GenerativeModel(
                model_name='models/gemini-1.5-flash-latest',
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1),
                safety_settings=self.no_safety,
                system_instruction=f"{config.BotConfig.bot_prompt_voice}\n{additional_info}"
            )
            messages = [{"role": "user", "parts": [{"text": f"{author.display_name} (голосовое сообщение)"},
                                                   {"inline_data": {"data": wav_data, "mime_type": "audio/wav"}}]}, ]

            res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                          contents=messages,
                                          tools=klaudy_tools.voice_tools, stream=True, generation_config=self.generation_config)
            res, tool_call_detector = itertools.tee(res, 2)
            maybe_tool_call_part = next(tool_call_detector).candidates[0].content.parts[0]
            if "function_call" not in maybe_tool_call_part:
                return map(lambda x: x.text, res)
            else:
                tool_call = maybe_tool_call_part.function_call

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.voice_tools, tool_call.name, klaudy_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools (ВОЙС): {tool_call.name}, {function_response}")

                messages.append(generate_function_response(tool_call.name, function_response))
                res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                              contents=messages, stream=True, generation_config=self.generation_config)
                return map(lambda x: x.text, res)
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return iter(["Ошибка со стороны гугла"])
        except Exception as e:
            logging.error(traceback.format_exc())
            return iter([f"Ошибка при генерации ответа"])

    async def generate_answer(self, messages, members=None, mes=None, additional_info=""):
        if members is None:
            members = {}
        try:
            model = genai.GenerativeModel(
                model_name='models/gemini-1.5-flash-latest',
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1),
                safety_settings=self.no_safety,
                system_instruction=f"{config.BotConfig.bot_prompt}\n{additional_info}",
            )
            res = await asyncio.to_thread(self.generate_gemini_1_5_flesh, model=model,
                                          contents=messages,
                                          tools=klaudy_tools.text_tools, generation_config=self.generation_config)
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
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла: {e}"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка {e}"

    # Токен выбирается декоратором
    @utils.api_rate_limiter_with_ques(rate_limit=config.Gemini.rate_limit_model_1_5_flash, tokens=config.Gemini.tokens)
    def generate_gemini_1_5_flesh(self, *args, model, token=config.Gemini.token, **kwargs):
        genai.configure(api_key=token,
                        client_options={"api_endpoint": config.Gemini.server},
                        transport=config.Gemini.transport)

        res = model.generate_content(*args, **kwargs)
        return res
