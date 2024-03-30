import asyncio
import logging
import time

import aiohttp
import discord
import google.api_core.exceptions
import html2text
import google.generativeai as genai
import openai
from google.generativeai.types import HarmBlockThreshold
import google.ai.generativelanguage as glm

from bs4 import BeautifulSoup
import traceback

import config
import klaudy_tools
import utils
import voice_music
from voice import VoiceConnect


class QueTimoutError(Exception):
    pass


class GPT:
    def __init__(self, bot):
        self.tts_que = [[] for _ in range(len(config.openai_tokens))]
        self.tts_count = [3 for _ in range(len(config.openai_tokens))]
        self.html2text_client = html2text.HTML2Text()
        self.html2text_client.ignore_links = True
        self.html2text_client.ignore_images = True
        self.html2text_client.unicode_snob = True
        self.html2text_client.decode_errors = 'replace'
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

        self.openai_client = openai.AsyncOpenAI(
            api_key=config.openai_token,
            base_url=config.openai_server,
            max_retries=0,
            timeout=config.openai_timeout
        )
        self.bot: discord.Client = bot
        self.voice_connections = {}

    async def get_member_text(self, member):
        try:
            info_message = f"\nНик: {member.name} \nОтображаемое имя: \n{member.display_name} \nУпоминание(тег): {member.mention}"
            if member.activity:
                attrs = [
                    ('Имя ', member.activity.name),
                    ('детали', ""),
                ]
                try:
                    attrs[1] = ("детали", member.activity.details)
                except Exception:
                    pass
                inner = ' '.join(" - ".join(t) for t in attrs if t[1] is not None)
                info_message += f"\nАктивность: {inner}"
                types = ("Играет", "Стримит", "Слушает", "Смотрит", "Другое", "Соревнуется", "Неизвестно")
                if member.activity.type is not None and member.activity.type.value != -1:
                    info_message += f" Тип активности - {types[member.activity.type.value]}"
            if member.bot:
                info_message += f"\nДанный пользователь является ботом."
            else:
                info_message += f"\nДанный пользователь не является ботом."
            return info_message
        except Exception as e:
            logging.warning(f"get_member_text - {e}")
            return f"Ошибка {e}"

    async def get_member(self, nick, members):
        try:
            if nick == "discord_bot":
                return f"Пользователь является ботом дискорд."
            nick = nick.replace("-", ".")
            member = members.get(nick)
            if not member:
                return f"Пользователь {nick} не найден"
            return await self.get_member_text(member)
        except Exception as e:
            logging.warning(f"get_member - {e}")
            return f"Ошибка {e}"

    async def enjoy_voice(self, message: discord.Message):
        try:
            if not message.author.voice:
                return "ты не в голосовом канале"
            current_voice = self.voice_connections.get(message.guild.id)
            if current_voice:
                if current_voice.vch.id == message.author.voice.channel.id:
                    return "Уже в голосовом канале"
                await current_voice.exit()
                await asyncio.sleep(1)
            self.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self)
            return "Успешно зашёл в голосовой канал"
        except Exception as e:
            logging.warning(f"enjoy_voice - {e}")
            return f"Ошибка {e}"

    async def simple_link_checker(self, url):
        """
        Версия проверки ссылок без использования нейросети от Яндекса (просто текст страницы)
        В данный момент не используется
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, timeout=config.requests_timeout) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                    if len(text) > 2000:
                        text = text[:2000]
                    return text
        except Exception as e:
            logging.warning(f"simple_link_checker - {e}")
            return f"Ошибка {e}"

    async def link_checker(self, url):
        """
        Проверяет текстовое содержание ссылки.
        Если текста не много, использует его
        Если много, то использует нейросеть от Яндекса 300.ya.ru для выделения главного
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with await aiohttp_session.get(url, timeout=config.requests_timeout) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                if len(text) < 1200:
                    if len(text) > 1000:
                        text = text[:1000] + "..."
                    return text
                auth = f'OAuth {config.ya300_token}'
                async with await aiohttp_session.post(config.ya300_server, json={"article_url": url},
                                                      headers={"Authorization": auth},
                                                      timeout=config.requests_timeout) as response:
                    data = await response.json()

                if data["status"] != "success":
                    text = text[:1000] + "..."
                    return text
                async with aiohttp_session.get(data["sharing_url"], timeout=config.requests_timeout) as res:
                    res.encoding = 'UTF-8'
                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Находим все элементы, соответствующие селектору '.thesis-text span'
                    res = f"{soup.select('h1.title')[0].text}\n"
                    thesis_elements = soup.select('.thesis-text span')
                    for i in thesis_elements:
                        if len(i.text) > 2:
                            res += f"{i.text}\n"

                    if len(res) > 1000:
                        res = res[:1000] + '...'
                    return res
        except Exception as e:
            logging.warning(f"link_checker - {e}")
            return f"Ошибка {e}"

    async def search_gif_on_tenor(self, query):
        try:
            api_key = config.tenor_token
            url = config.tenor_server

            params = {
                'q': query,
                'key': api_key,
                'limit': 1,
                'ckey': "my_test_app"
            }
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, params=params, timeout=config.requests_timeout) as response:
                    data = await response.json()
                    if len(data['results']) == 0:
                        return "`Не нашлось гифок`"
                    gif_url = data['results'][0]['media_formats']["gif"]["url"]
                    return gif_url
        except Exception as e:
            logging.warning(f"search_gif_on_tenor - {e}")
            return f"Ошибка {e}"

    async def play_from_text(self, query, message: discord.Message):
        try:
            voice = self.voice_connections.get(message.guild.id)
            if voice is None:
                if not message.author.voice:
                    return "`ты не в голосовом канале`"
                self.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self)
                voice = self.voice_connections[message.guild.id]
            while voice.mixer_player is None:
                await asyncio.sleep(0.2)
            return f"`{await voice_music.play_music(query, voice.mixer_player)}`"
        except Exception as e:
            logging.warning(f"play_from_text - {e}")
            return f"`Ошибка {e}`"

    async def stop_from_text(self, message: discord.Message):
        try:
            voice = self.voice_connections.get(message.guild.id)
            if voice is None:
                return "сейчас не играет музыка"
            return await voice_music.off_music(voice.mixer_player)
        except Exception as e:
            logging.warning(f"stop_from_text - {e}")
            return f"Ошибка {e}"

    async def get_que_from_text(self, message: discord.Message):
        try:
            voice = self.voice_connections.get(message.guild.id)
            if voice is None:
                return "сейчас не играет музыка"
            que = await voice_music.get_que(voice.mixer_player)
            return f"`{que}`"
        except Exception as e:
            logging.warning(f"get_que_from_text - {e}")
            return f"Ошибка {e}"

    async def fake_func(self, *args, **kwargs):
        return "Ты пытаешься вызвать несуществующую функцию"

    def stop_log(self, res):
        finish_reasons = {1: "баг в Клауди", 2: "лимит длинны запроса/ответа", 3: "цензура блочит", 4: "повторяющиеся токены в запросе", 5: "баг на стороне гуглов"}
        logging.info(f"Ошибка при генерации ответа {finish_reasons[res.candidates[0].finish_reason]}, {res.candidates[0].safety_ratings}")
        return f"Ошибка при генерации ответа `{finish_reasons[res.candidates[0].finish_reason]}`"

    async def generate_answer_in_voice(self, query, author, channel: discord.VoiceChannel, client: discord.VoiceClient, voice_history):
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
                return self.stop_log(res)
            if 'function_call' not in res.candidates[0].content.parts[0]:
                return res.text
            else:
                tool_call = res.candidates[0].content.parts[0].function_call
                available_functions = {
                    "play_music": voice_music.play_music,
                    "off_music": voice_music.off_music,
                    "get_que": voice_music.get_que,
                    # "leave_voice": (lambda: print("Я ливаю", client.disconnect()), ()),  # Отключил, слишком часто использует
                }

                messages.append(
                    glm.Content(parts=[glm.Part(
                        function_call=glm.FunctionCall(
                            name=tool_call.name,
                            args=tool_call.args))], role="model")
                )
                function_to_call = available_functions.get(tool_call.name, self.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name in ("play_music", "off_music", "get_que"):
                    func_kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player

                function_response = await function_to_call(**func_kwargs)
                logging.info(f"tools (ВОЙС): {tool_call.name}, {function_response}")

                messages.append(
                    glm.Content(parts=[glm.Part(
                        function_response=glm.FunctionResponse(
                            name=tool_call.name,
                            response={"response": function_response}))], role="function")
                )
                res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages)
                if not res.parts:
                    return self.stop_log(res)
                result_text = res.text
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла `{e}`"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка `{e}`"

    async def generate_image_answer(self, messages):
        try:
            res = self.gemini_image_model.generate_content(
                contents=messages,
            )
            if not res.parts:
                return self.stop_log(res)
            return res.text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла `{e}`"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка `{e}`"

    async def generate_answer(self, messages, members=None, mes=None):
        if members is None:
            members = {}
        try:
            res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages, tools=klaudy_tools.text_tools)
            if not res.parts:
                return self.stop_log(res)
            if 'function_call' not in res.candidates[0].content.parts[0]:
                return res.text
            else:
                tools_logs = []
                tool_call = res.candidates[0].content.parts[0].function_call
                available_functions = {
                    "search_gif_on_tenor": self.search_gif_on_tenor,
                    "link_checker": self.link_checker,
                    "enjoy_voice": self.enjoy_voice,
                    "play_from_text": self.play_from_text,
                    "stop_from_text": self.stop_from_text,
                    "get_que_from_text": self.get_que_from_text,
                    # "get_member": (self.get_member, ("nick",)),  # временно отключено, бот слишком часто её использовал
                }

                messages.append(
                    glm.Content(parts=[glm.Part(
                        function_call=glm.FunctionCall(
                            name=tool_call.name,
                            args=tool_call.args))], role="model")
                )
                # messages.append(
                #     {
                #         "role": "model",
                #         "parts": [{
                #             "functionCall": {
                #                 "name": tool_call.name,
                #                 "args": func_kwargs
                #             }
                #         }]
                #     }
                # )
                # На данный момент API Gemini находится в бете, и функции из за бага принимает только так

                function_to_call = available_functions.get(tool_call.name, self.fake_func)

                func_kwargs = {i: tool_call.args[i] for i in tool_call.args}
                if tool_call.name == "get_member":
                    func_kwargs["members"] = members
                if tool_call.name in ("enjoy_voice", "play_from_text", "stop_from_text", "get_que_from_text"):
                    func_kwargs["message"] = mes

                function_response = await function_to_call(**func_kwargs)

                if tool_call.name in ("search_gif_on_tenor", "play_from_text", "get_que_from_text"):
                    tools_logs.append(function_response)
                logging.info(f"tools: {tool_call.name}, {func_kwargs} {function_response}")
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
                messages.append(
                    glm.Content(parts=[glm.Part(
                        function_response=glm.FunctionResponse(
                            name=tool_call.name,
                            response={"response": function_response}))], role="function")
                )
                res = await asyncio.to_thread(self.gemini_model.generate_content, contents=messages)
                if not res.parts:
                    return self.stop_log(res)
                result_text = res.text
                for i in tools_logs:
                    result_text += f"\n{i}"
                return result_text
        except google.api_core.exceptions.GoogleAPIError as e:
            logging.error(traceback.format_exc())
            return f"Ошибка со стороны гугла `{e}`"
        except Exception as e:
            logging.error(traceback.format_exc())
            return f"Ошибка `{e}`"

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
