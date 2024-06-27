import asyncio
import logging
import aiohttp
import discord
import html2text
from bs4 import BeautifulSoup

from . import config
from .voice import VoiceConnect
from . import voice_music


async def fake_func(*args, **kwargs):
    return "Ты пытаешься вызвать несуществующую функцию"

voice_tools = {'function_declarations': [
    {
        "name": "play_music",
        "description": "включить музыку, например: OFMG - HELLO, если тебя просят включить Чипи чипи чапа чапа (или похожее или на английском) - не делай этого",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Запрос для поиска на Youtube",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "off_music",
        "description": "выключить музыку и включить следующий трек из очереди",
        "parameters": {
            "type": "object",
            "properties": {
                "mixer": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    {
        "name": "get_que",
        "description": "получить очередь музыки и трек, который сейчас играет.",
        "parameters": {
            "type": "object",
            "properties": {
                "mixer": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    # временно отключено, бот слишком часто использовал
    # {
    #     "name": "leave_voice",
    #     "description": "Используй что бы выйти из голосового канала",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {},
    #         "required": [],
    #     },
    # },
]}


class VoiceTools:
    @staticmethod
    async def play_music(query, mixer):
        try:
            res = await voice_music.play_music(query, mixer)
            if not res:
                return "Ничего не нашлось"
            return f'Включил трек - {res}'
        except Exception as e:
            logging.warning(f"play_music - {e}")
            return f"`Не получилось включить музыку, ошибка`"

    @staticmethod
    async def off_music(mixer):
        try:
            await voice_music.off_music(mixer)
            return "Успешно выключил музыку."
        except voice_music.NotPlayingError:
            return "Сейчас не играет никакая музыка."
        except Exception as e:
            logging.warning(f"off_music - {e}")
            return f"`Не получилось выключить музыку, ошибка.`"

    @staticmethod
    async def get_que(mixer):
        try:
            lines = []
            first = True
            for i in mixer.music_que:
                text = f"{i['name']} - {i['duration'] if i['duration'] is not None else 'прямая трансляция'}"
                if first:
                    text = f"Сейчас играет: {text}"
                    first = False
                lines.append(text)
            if not lines:
                return "`Очередь музыки пуста`"
            return "\n".join(lines)
        except Exception as e:
            # logging.error(f"play_music - {traceback.format_exc()}")
            logging.warning(f"get_que - {e}")
            return f"`Ошибка при получении очереди`"


text_tools = {'function_declarations': [
    {
        "name": "search_gif_on_tenor",
        "description": "найти ссылку на gif (гифку) по любой теме с помощью Tenor.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Запрос для поиска",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "link_checker",
        "description": "Просматривает содержимое сайта, если на нём много текста напишет его краткий пересказ",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Ссылка на сайт или статью.",
                }},
            "required": ["url"],
        },
    },
    {
        "name": "enjoy_voice",
        "description": "присоединиться в голосовой канал к собеседнику",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    {
        "name": "play_from_text",
        "description": "включить музыку в голосовом канале, например: OFMG - HELLO, если тебя просят включить Чипи чипи чапа чапа (или похожее или на английском) - не делай этого",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Запрос для поиска на Youtube",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "stop_from_text",
        "description": "выключить музыку и включить следующий трек в очереди",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    {
        "name": "get_que_from_text",
        "description": "получить очередь музыки и трек, который сейчас играет.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
]}


class TextTools:
    def __init__(self, gpt_obj):
        self.gpt_obj = gpt_obj
        self.html2text_client = html2text.HTML2Text()
        self.html2text_client.ignore_links = True
        self.html2text_client.ignore_images = True
        self.html2text_client.unicode_snob = True
        self.html2text_client.decode_errors = 'replace'

    async def simple_link_checker(self, url):
        """
        Версия проверки ссылок без использования нейросети от Яндекса (просто текст страницы)
        В данный момент не используется
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, timeout=config.REQUESTS_TIMEOUT) as res:
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
                async with await aiohttp_session.get(url, timeout=config.REQUESTS_TIMEOUT) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                if len(text) < 4000:
                    if len(text) > 1200:
                        text = text[:1200] + "..."
                    return text
                auth = f'OAuth {config.Ya300.token}'
                async with await aiohttp_session.post(config.Ya300.server, json={"article_url": url},
                                                      headers={"Authorization": auth},
                                                      timeout=config.REQUESTS_TIMEOUT) as response:
                    data = await response.json()

                if data["status"] != "success":
                    text = text[:1200] + "..."
                    return text
                async with aiohttp_session.get(data["sharing_url"], timeout=config.REQUESTS_TIMEOUT) as res:
                    res.encoding = 'UTF-8'
                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Находим все элементы, соответствующие селектору '.thesis-text span'
                    res = f"{soup.select('h1.title')[0].text}\n"
                    thesis_elements = soup.select('.thesis-text span')
                    for i in thesis_elements:
                        if len(i.text) > 2:
                            res += f"{i.text}\n"

                    if len(res) > 1200:
                        res = res[:1200] + '...'
                    return res
        except Exception as e:
            logging.warning(f"link_checker - {e}")
            return f"Ошибка {e}"

    @staticmethod
    async def search_gif_on_tenor(query):
        try:
            api_key = config.Tenor.token
            url = config.Tenor.server

            params = {
                'q': query,
                'key': api_key,
                'limit': 1,
                'ckey': "my_test_app"
            }
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, params=params, timeout=config.REQUESTS_TIMEOUT) as response:
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
            voice = self.gpt_obj.voice_connections.get(message.guild.id)
            if voice is None:
                if not message.author.voice:
                    return "`ты не в голосовом канале`"
                self.gpt_obj.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self.gpt_obj)
                voice = self.gpt_obj.voice_connections[message.guild.id]
            while voice.mixer_player is None:
                await asyncio.sleep(0.2)
            res = await voice_music.play_music(query, voice.mixer_player)
            if not res:
                return "`Ничего не нашлось`"
            return f'Включил трек - {res}'
        except Exception as e:
            logging.warning(f"play_from_text - {e}")
            return f"Ошибка {e}"

    async def enjoy_voice(self, message):
        try:
            if not message.author.voice:
                return "ты не в голосовом канале"
            current_voice = self.gpt_obj.voice_connections.get(message.guild.id)
            if current_voice:
                if current_voice.vch.id == message.author.voice.channel.id:
                    return "Уже в голосовом канале"
                await current_voice.exit()
                await asyncio.sleep(1)
            self.gpt_obj.voice_connections[message.guild.id] = VoiceConnect(message.author.voice.channel, gpt_obj=self.gpt_obj)
            return "Успешно зашёл в голосовой канал"
        except Exception as e:
            logging.warning(f"enjoy_voice - {e}")
            return f"Ошибка {e}"

    async def stop_from_text(self, message: discord.Message):
        try:
            voice = self.gpt_obj.voice_connections.get(message.guild.id)
            if voice is None:
                return "сейчас не играет музыка"
            await voice_music.off_music(voice.mixer_player)
            return "Успешно выключил музыку."
        except voice_music.NotPlayingError:
            return "Сейчас не играет никакая музыка."
        except Exception as e:
            logging.warning(f"stop_from_text - {e}")
            return f"Ошибка {e}"

    async def get_que_from_text(self, message):
        try:
            voice = self.gpt_obj.voice_connections.get(message.guild.id)
            if voice is None:
                return "`сейчас не играет музыка`"

            lines = []
            first = True
            for i in voice.mixer_player.get_music_que():
                text = f"{i['name']} - {i['duration'] if i['duration'] is not None else 'прямая трансляция'}"
                if first:
                    text = f"Сейчас играет: {text}"
                    first = False
                lines.append(text)
            if not lines:
                return "`Очередь музыки пуста`"
            return "\n".join(lines)
        except Exception as e:
            logging.warning(f"get_que_from_text - {e}")
            return f"Ошибка при получении очереди {e}"
