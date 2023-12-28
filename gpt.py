import asyncio
import json
import logging
import time
import aiohttp
import discord
import html2text
import openai
from bs4 import BeautifulSoup
import traceback

import config
import clyde_tools
import utils
import voice_music
from voice import VoiceConnect


class GPT:
    def __init__(self, bot):
        self.openai_que = [[] for _ in range(len(config.openai_tokens))]
        self.openai_message_count = [3 for _ in range(len(config.openai_tokens))]
        self.tts_que = [[] for _ in range(len(config.openai_tokens))]
        self.tts_count = [3 for _ in range(len(config.openai_tokens))]
        self.model_number = 0
        self.models_dead = False
        self.html2text_client = html2text.HTML2Text()
        self.html2text_client.ignore_links = True
        self.html2text_client.ignore_images = True
        self.html2text_client.unicode_snob = True
        self.html2text_client.decode_errors = 'replace'
        self.openai_client = openai.AsyncOpenAI(
                api_key=config.openai_token,
                base_url=config.chatgpt_server,
                max_retries=0
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
            return f"Ошибка {e}"

    async def enjoy_voice(self, message: discord.Message):
        try:
            if not message.author.voice:
                return "автор не в голосовом канале"
            current_voice = self.voice_connections.get(message.guild.id)
            if current_voice.vch.id == message.author.voice.channel.id:
                return "Уже в голосовом канале"
            if current_voice:
                await current_voice.exit()
                await asyncio.sleep(0.3)
            self.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self)
            return "Успешно зашёл в голосовой канал"
        except Exception as e:
            return f"Ошибка {e}"

    async def simple_link_checker(self, url):
        """
        Версия проверки ссылок без использования нейросети от Яндекса (просто текст страницы)
        В данный момент не используется
        """
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                    if len(text) > 2000:
                        text = text[:2000]
                    return text
        except Exception as e:
            return f"Ошибка {e}"

    async def link_checker(self, url):
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with await aiohttp_session.get(url) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                if len(text) < 2500:
                    if len(text) > 2000:
                        text = text[:1950] + "..."
                    return text
                auth = f'OAuth {config.ya300_token}'
                async with await aiohttp_session.post(config.ya300_server, json={"article_url": url},
                                                      headers={"Authorization": auth}) as response:
                    data = await response.json()

                if data["status"] != "success":
                    text = text[:1950] + "..."
                    return text
                async with aiohttp_session.get(data["sharing_url"]) as res:
                    res.encoding = 'UTF-8'
                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Находим все элементы, соответствующие селектору '.thesis-text span'
                    res = f"{soup.select('h1.title')[0].text}\n"
                    thesis_elements = soup.select('.thesis-text span')
                    for i in thesis_elements:
                        if len(i.text) > 2:
                            res += f"{i.text}\n"

                    if len(res) > 2000:
                        res = res[:1950] + '...'
                    return res
        except Exception as e:
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
                async with aiohttp_session.get(url, params=params) as response:
                    data = await response.json()
                    gif_url = data['results'][0]['media_formats']["gif"]["url"]
                    return gif_url
        except Exception as e:
            return f"Ошибка {e}"

    async def play_from_text(self, query, message: discord.Message):
        voice = self.voice_connections.get(message.guild.id)
        if voice is None:
            if not message.author.voice:
                return "ты не в голосовом канале"
            self.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self)
            voice = self.voice_connections[message.guild.id]
        while voice.mixer_player is None:
            await asyncio.sleep(0.2)
        return await voice_music.play_music(query, voice.mixer_player)

    async def stop_from_text(self, message: discord.Message):
        voice = self.voice_connections.get(message.guild.id)
        if voice is None:
            return "сейчас не играет музыка"
        return await voice_music.off_music(voice.mixer_player)

    async def fake_func(self, *args, **kwargs):
        return "Ты пытаешься вызвать несуществующую функцию"

    async def voice_gpt(self, query, author, channel: discord.VoiceChannel, client: discord.VoiceClient):
        info_message = f"""Информация о голосовом чате
                    Название сервера: {channel.guild.name}
                    Название голосового канала: {channel.name}"""
        if len(channel.members) < 12:
            info_message += f"\nСписок ников пользователей голосового чата чата: {', '.join([i.display_name for i in channel.members])}"
        messages = [{"role": "system", "content": config.clyde_knowns}, {"role": "system", "content": info_message},
                    {"role": "user", "content": f"{author.display_name}: {query}"}]
        try:
            res = await self.que_gpt(
                messages=messages,
                model=config.models[self.model_number],
                tools=clyde_tools.voice_tools, tool_choice="auto",
            )
            await asyncio.sleep(0.1)
            resp_message = res.choices[0].message
            if resp_message.tool_calls:
                tool_calls = resp_message.tool_calls
                available_functions = {
                    # "leave_voice": (lambda: print("Я ливаю", client.disconnect()), ()),  # Отключил, слишком часто использует
                    "play_music": (voice_music.play_music, ("query",)),
                    "off_music": (voice_music.off_music, ())
                }
                messages.append(resp_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name, (self.fake_func, ()))
                    function_args = json.loads(tool_call.function.arguments)
                    kwargs = {a: b for a, b in function_args.items() if a in function_to_call[1]}
                    if function_name in ("play_music", "off_music"):
                        kwargs["mixer"] = self.voice_connections[channel.guild.id].mixer_player
                    function_response = await function_to_call[0](**kwargs)
                    logging.info(f"ВОЙС: {function_name}, {function_response}")

                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                res = await self.que_gpt(
                    messages=messages,
                    model=config.models[self.model_number]
                )
                resp_message = res.choices[0].message
            self.models_dead = False
            return resp_message.content
        except openai.RateLimitError as e:
            if "RPM" in e.message:
                return f"Минутный рейт лимит"
            else:
                if self.models_dead:
                    return f"Дневной рейт лимит"
                self.models_dead = True
                self.model_number = (self.model_number + 1) % len(config.models)
                return await self.voice_gpt(messages, author=author, channel=channel, client=client)
        except openai.APITimeoutError:
            return f"Таймаут запроса"
        except Exception as e:
            return f"Ошибка {e}"

    async def chat_gpt(self, messages, members=None, mes=None):
        if members is None:
            members = {}
        try:
            res = await self.que_gpt(
                messages=messages,
                model=config.models[self.model_number],
                tools=clyde_tools.text_tools, tool_choice="auto",
            )
            await asyncio.sleep(0.1)
            resp_message = res.choices[0].message
            if resp_message.tool_calls:
                tool_calls = resp_message.tool_calls
                available_functions = {
                    "search_gif_on_tenor": (self.search_gif_on_tenor, ("query",)),
                    "link_checker": (self.link_checker, ("url",)),
                    "enjoy_voice": (self.enjoy_voice, ()),
                    "play_from_text": (self.play_from_text, ("query",)),
                    "stop_from_text": (self.stop_from_text, ())
                    # "get_member": (self.get_member, ("nick",)),  # временно отключено, бот слишком часто её использовал
                }
                messages.append(resp_message)
                gifs = []
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions.get(function_name, (self.fake_func, ()))
                    function_args = json.loads(tool_call.function.arguments)
                    kwargs = {a: b for a, b in function_args.items() if a in function_to_call[1]}
                    if function_name == "get_member":
                        kwargs["members"] = members
                    if function_name in ("enjoy_voice", "play_from_text", "stop_from_text"):
                        kwargs["message"] = mes

                    function_response = await function_to_call[0](**kwargs)

                    if function_name == "search_gif_on_tenor" and function_response.startswith("http"):
                        gifs.append(function_response)
                    logging.info(f"{function_name}, {function_response}")
                    messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response,
                        }
                    )
                res = await self.que_gpt(
                    messages=messages,
                    model=config.models[self.model_number]
                )
                resp_message = res.choices[0].message
                for i in gifs:
                    if i not in resp_message:
                        resp_message.content += f"\n{i}"

            self.models_dead = False
            return resp_message.content
        except openai.RateLimitError as e:
            # warning(e.message, e.status_code)
            if "RPM" in e.message:
                return f"Произошёл минутный рейт лимит ({len(config.openai_tokens) * 3} запроса в минуту, подожди)"
            else:
                if self.models_dead:
                    return f"Произошёл дневной рейт лимит (200 запросов в день)"
                self.models_dead = True
                self.model_number = (self.model_number + 1) % len(config.models)
                return await self.chat_gpt(messages, mes=mes)
        except openai.APITimeoutError:
            return f"Произошёл таймаут запроса (ошибка)"
        except Exception as e:
            traceback.print_exc()
            logging.warning(f"Ошибка {e}")
            return f"Ошибка {e}"

    async def simple_chat_gpt(self, prompt):
        # Не используется
        try:
            json_data = {"model": config.models[self.model_number], "messages": [{"role": "user", "content": prompt}]}
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.post(config.chatgpt_server, json=json_data,
                                                headers={"Authorization": f"Bearer {config.openai_token}"}) as res:
                    res = await res.json()
                    return res["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Ошибка {e}"

    async def timer_reset_gpt(self, my_num):
        await asyncio.sleep(60)
        if self.openai_message_count[my_num] != 3:
            self.openai_message_count[my_num] += 1

    async def que_gpt(self, **kwargs):
        my_num, _ = max(enumerate(self.openai_message_count), key=lambda x: x[1])
        if self.openai_que[my_num] or self.openai_message_count[my_num] <= 0:
            my = time.time()
            my_num, my_que = min(enumerate(self.openai_que), key=lambda x: len(x[1]))
            my_que.append(my)
            while my in self.openai_que[my_num]:
                await asyncio.sleep(1)
        self.openai_message_count[my_num] -= 1
        self.openai_client.api_key = config.openai_tokens[my_num]
        res = await self.openai_client.chat.completions.create(**kwargs)
        utils.run_in_thread(self.timer_reset_gpt(my_num))
        return res

    async def que_progress(self):
        while True:
            for i in range(len(self.openai_que)):
                sleep_count = min(len(self.openai_que[i]), self.openai_message_count[i])
                for _ in range(sleep_count):
                    self.openai_que[i].pop(0)
                    await asyncio.sleep(1)
            await asyncio.sleep(0.1)

    async def que_tts(self, **kwargs):
        my_num, _ = max(enumerate(self.tts_count), key=lambda x: x[1])
        if self.tts_que[my_num] or self.tts_count[my_num] <= 0:
            my = time.time()
            my_num, my_que = min(enumerate(self.tts_que), key=lambda x: len(x[1]))
            my_que.append(my)
            while my in self.tts_que[my_num]:
                await asyncio.sleep(1)
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
