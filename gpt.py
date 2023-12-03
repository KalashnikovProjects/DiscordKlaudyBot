import asyncio
import json
import logging
import time

import aiohttp
import discord
import html2text
import openai
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
import config


class GPT:
    voice_tools = [
        {
            "type": "function",
            "function": {
                "name": "leave_voice",
                "description": f"функция, что бы выйти из голосового канала (его также называют гс или войс), используй ТОЛЬКО если просят выйти с указанием твоего имени, например: Выйди из войса, {config.name}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {},
                    },
                    "required": [],
                },
            }}
    ]

    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_gif_on_tenor",
                "description": "находит ссылку на gif (гифку) по любой теме с помощью Tenor. Вставь эту ссылку в своё сообщение что бы в чате увидели гифку.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Запрос, по которому нужно найти gif (обычно не более 5 слов)",
                        }},
                },
                "required": ["query"],
            },
        },
        {
            "type": "function",
            "function": {
                "name": "link_checker",
                "description": "просматривает содержимое сайта, если на нём много текста напишет его краткий пересказ с помощью нейросети YandexGPT.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Ссылка на сайт или статью",
                        }},
                },
                "required": ["url"],
            },
        },
        {
            "type": "function",
            "function": {
                "name": "enjoy_voice",
                "description": "Присоединяет бота (тебя) к голосовому каналу дискорд (их также называют гс или войс), в котором находится отправитель сообщения.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
                "required": [],
            },
        },
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "get_member",
        #         "description": "получает информацию о пользователе по его никнейму (не по имени) (статус, отображаемое имя, его активность, является ли он ботом и его тег (упоминание)). Используй только если пользователь просит узнать о ком то информацию в своём сообщении и если это не ты.",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {
        #                 "nick": {
        #                     "type": "string",
        #                     "description": "Ник пользователя, которого нужно найти, за ним нужно обратиться к списку ников участников",
        #                 }},
        #         },
        #         "required": ["nick"],
        #     },
        # }
    ]

    def __init__(self):
        self.openai_que = []
        self.openai_message_count = 3
        self.tts_que = []
        self.tts_count = 3
        self.model_number = 0
        self.models_dead = False
        self.html2text_client = html2text.HTML2Text()
        self.html2text_client.ignore_links = True
        self.html2text_client.ignore_images = True
        self.html2text_client.unicode_snob = True
        self.html2text_client.decode_errors = 'replace'
        self.openai_client = AsyncOpenAI(
                # defaults to os.environ.get("OPENAI_API_KEY")
                api_key=config.openai_token,
                base_url=config.chatgpt_server,
                max_retries=1
        )

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

    async def enjoy_voice(self, message):
        try:
            if not message.author.voice:
                return f"Автор сообщения не в голосовом канале, сначала ему нужно зайти."
            voice_channel = message.author.voice.channel
            from voice import VoiceConnect
            voice_client = VoiceConnect()
            await asyncio.create_task(voice_client.enter_voice(voice_channel, gpt_obj=self))
            return "Успешно зашёл в голосовой канал"
        except Exception as e:
            return f"Ошибка {e}"

    async def simple_link_checker(self, url):
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

    async def timer_reset(self):
        await asyncio.sleep(60)
        if self.openai_message_count != 3:
            self.openai_message_count += 1

    async def que_gpt(self, **kwargs):
        if self.openai_que or self.openai_message_count == 0:
            my = time.time()
            self.openai_que.append(my)
            while my in self.openai_que:
                await asyncio.sleep(1)
        self.openai_message_count -= 1
        res = await self.openai_client.chat.completions.create(**kwargs)
        asyncio.create_task(self.timer_reset())
        return res

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
                # tools=self.voice_tools, tool_choice="auto",
            )
            await asyncio.sleep(0.1)
            resp_message = res.choices[0].message
            if resp_message.tool_calls:
                tool_calls = resp_message.tool_calls
                available_functions = {
                    "leave_voice": (client.disconnect, ())
                }
                messages.append(resp_message)
                for tool_call in tool_calls:
                    logging.debug("ББ я ливаю")
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    kwargs = {a: b for a, b in function_args.items() if a in function_to_call[1]}
                    function_response = await function_to_call[0](**kwargs)
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
                tools=self.tools, tool_choice="auto",
            )
            await asyncio.sleep(0.1)
            resp_message = res.choices[0].message
            if resp_message.tool_calls:
                tool_calls = resp_message.tool_calls
                available_functions = {
                    "search_gif_on_tenor": (self.search_gif_on_tenor, ("query",)),
                    "link_checker": (self.link_checker, ("url",)),
                    "get_member": (self.get_member, ("nick",)),  # временно отключено
                    "enjoy_voice": (self.enjoy_voice, ())
                }
                messages.append(resp_message)
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_to_call = available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    kwargs = {a: b for a, b in function_args.items() if a in function_to_call[1]}
                    if function_name == "get_member":
                        kwargs["members"] = members
                    if function_name == "enjoy_voice":
                        kwargs["message"] = mes
                    function_response = await function_to_call[0](**kwargs)
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
            # warning(e.message, e.status_code)
            if "RPM" in e.message:
                return f"Произошёл минутный рейт лимит (3 запроса в минуту, подожди)"
            else:
                if self.models_dead:
                    return f"Произошёл дневной рейт лимит (200 запросов в день)"
                self.models_dead = True
                self.model_number = (self.model_number + 1) % len(config.models)
                return await self.chat_gpt(messages, mes=mes)
        except openai.APITimeoutError:
            return f"Произошёл таймаут запроса (ошибка)"
        except Exception as e:
            return f"Ошибка {e}"

    async def simple_chat_gpt(self, prompt):
        try:
            json_data = {"model": config.models[self.model_number], "messages": [{"role": "user", "content": prompt}]}
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.post(config.chatgpt_server, json=json_data,
                                                headers={"Authorization": f"Bearer {config.openai_token}"}) as res:
                    res = await res.json()
                    return res["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Ошибка {e}"

    async def que_progress(self):
        while True:
            sleep_count = min(len(self.openai_que), self.openai_message_count)
            for i in range(sleep_count):
                self.openai_que.pop(0)
                await asyncio.sleep(1.5)
            await asyncio.sleep(3)

    async def tts_que_progress(self):
        while True:
            sleep_count = min(len(self.tts_que), self.tts_count)
            for i in range(sleep_count):
                self.tts_que.pop(0)
                await asyncio.sleep(1.5)
            await asyncio.sleep(3)

    async def que_tts(self, **kwargs):
        if self.tts_que or self.tts_count == 0:
            my = time.time()
            self.tts_que.append(my)
            while my in self.tts_que:
                await asyncio.sleep(1)
        self.tts_count -= 1
        res = await self.openai_client.audio.speech.create(**kwargs)
        asyncio.create_task(self.tts_timer_reset())
        return res

    async def tts_timer_reset(self):
        await asyncio.sleep(60)
        if self.tts_count != 3:
            self.tts_count += 1
