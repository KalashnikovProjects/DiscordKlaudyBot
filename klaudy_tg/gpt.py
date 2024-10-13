import asyncio
import json
import logging
import random
import traceback

import aiohttp
from retry import retry

import google.api_core.exceptions
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold

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


async def upload_file(data, content_type, filename):
    r = random.randint(0, 1000000000)
    num_bytes = len(data)

    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(num_bytes),
        "Content-Type": "application/json"
    }
    if content_type:
        headers['X-Goog-Upload-Header-Content-Type'] = content_type
    json_data = json.dumps({"file": {"display_name": f"{r}-{filename}"}})

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
    finish_reasons = {1: "баг в Клауди", 2: "лимит длинны запроса/ответа", 3: "цензура блочит",
                      4: "повторяющиеся токены в запросе", 5: "баг на стороне гуглов"}
    logging.info(
        f"Ошибка при генерации ответа {finish_reasons[res.candidates[0].finish_reason]}, {res.candidates[0].safety_ratings}")
    logging.debug(res)
    return f"Ошибка при генерации ответа `{finish_reasons[res.candidates[0].finish_reason]}`"


class GPT:
    def __init__(self):
        self.generation_config = genai.types.GenerationConfig(
            temperature=config.Gemini.temperature,
            max_output_tokens=config.Gemini.max_output_tokens,
            candidate_count=1)

        self.no_safety = {i: HarmBlockThreshold.BLOCK_NONE for i in range(7, 11)}
        # Отключаем цензуру, у нас бот токсик

        self.text_tools = gpt_tools.TextTools(gpt_obj=self)

    @retry(tries=3, delay=2)
    async def generate_answer(self, messages, additional_info=""):
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
                return res.text
            else:
                tools_logs = []
                tool_call = func_call[0]

                messages.append(generate_function_call(tool_call.name, tool_call.args))

                function_to_call = getattr(self.text_tools, tool_call.name, gpt_tools.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
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
    @retry(tries=3, delay=2)
    @utils.api_rate_limiter_with_ques(rate_limit=config.Gemini.main_rate_limit, tokens=config.Gemini.tokens)
    def generate_gemini_1_5_flesh(self, *args, model, token=config.Gemini.token, **kwargs):
        genai.configure(api_key=token,
                        client_options={"api_endpoint": config.Gemini.server},
                        transport=config.Gemini.transport)
        res = model.generate_content(*args, **kwargs)
        return res
