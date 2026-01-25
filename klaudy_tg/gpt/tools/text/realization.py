import asyncio
import logging
import traceback

import aiohttp
import discord
from bs4 import BeautifulSoup
from discord import Member

from klaudy import config
from klaudy.audio import voice_music
from klaudy.audio.voice import VoiceConnect
from klaudy.audio.voice_connections import VoiceConnections
from klaudy import message_convertor



class TextTools:
    @staticmethod
    async def link_checker(url: str) -> str:
        """
        Проверяет текстовое содержание ссылки.
        Если текста не много, использует его
        Если много, то использует нейросеть от Яндекса 300.ya.ru для выделения главного
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                auth = f'OAuth {config.Ya300.token}'
                async with await aiohttp_session.post(config.Ya300.server, json={"article_url": url},
                                                      headers={"Authorization": auth},
                                                      timeout=config.REQUESTS_TIMEOUT) as response:
                    data = await response.json()
                if data["status"] != "success":
                    return "Не удалось получить данные сайта"
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
    async def search_gif_on_tenor(query: str) -> str:
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

    @staticmethod
    async def play_from_text(query: str, message: discord.Message, voice_connections: VoiceConnections, bot_user_id: int) -> str:
        try:
            voice = voice_connections.get_voice_connection(message.guild.id)
            if voice is None:
                if not message.author.voice:
                    return "`ты не в голосовом канале`"
                voice = VoiceConnect(bot_user_id, message.author.voice.channel, voice_connections)
                voice_connections.add_connection(message.guild.id, voice)
                await voice.connect()
            while voice.mixer_player is None:
                await asyncio.sleep(0.2)
            res = await voice_music.play_music(query, voice.mixer_player)
            if not res:
                return "`Ничего не нашлось`"
            return f'Включил трек - {res}'
        except Exception as e:
            print(traceback.format_exc())
            logging.warning(f"play_from_text - {e}")
            return f"Ошибка {e}"

    @staticmethod
    async def enjoy_voice(message: discord.Message, voice_connections: VoiceConnections, bot_user_id: int) -> str:
        try:
            if not message.author.voice:
                return "ты не в голосовом канале"
            current_voice = voice_connections.get_voice_connection(message.guild.id)
            if current_voice:
                if current_voice.voice_channel.id == message.author.voice.channel.id:
                    return "Уже в голосовом канале"
                try:
                    await current_voice.move_to_channel(message.author.voice.channel)
                except Exception as e:
                    await current_voice.exit()
                    voice = VoiceConnect(bot_user_id, message.author.voice.channel, voice_connections)
                    voice_connections.add_connection(message.guild.id, voice)
                    await voice.connect()
            else:
                voice = VoiceConnect(bot_user_id, message.author.voice.channel, voice_connections)
                voice_connections.add_connection(message.guild.id, voice)
                await voice.connect()
            return "Успешно зашёл в голосовой канал"
        except Exception as e:
            logging.warning(f"enjoy_voice - {e}")
            return f"Ошибка {e}"

    @staticmethod
    async def stop_from_text(message: discord.Message, voice_connections: VoiceConnections) -> str:
        try:
            voice = voice_connections.get_voice_connection(message.guild.id)
            if voice is None:
                return "сейчас не играет музыка"
            await voice_music.off_music(voice.mixer_player)
            return "Успешно выключил музыку."
        except voice_music.NotPlayingError:
            return "Сейчас не играет никакая музыка."
        except Exception as e:
            logging.warning(f"stop_from_text - {e}")
            return f"Ошибка {e}"

    @staticmethod
    async def get_que_from_text(message: discord.Message, voice_connections: VoiceConnections) -> str:
        try:
            voice = voice_connections.get_voice_connection(message.guild.id)
            if voice is None:
                return "`сейчас не играет музыка`"

            lines = []
            first = True
            for i in voice.mixer_player.get_music_que():
                text = f"{i.name} - {i.duration if i.duration is not None else 'прямая трансляция'}"
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

    @staticmethod
    async def send_personal_message(string: str, message: discord.Message, members: dict[str, Member]) -> str:
        try:
            await message.author.send(message_convertor.convert_ai_answer_to_message_text(string, members))
            return "Успешно отправлено"
        except Exception as e:
            logging.warning(f"send_personal_message - {e}")
            return f"Ошибка: {e}"

    @staticmethod
    async def dialog_pause():
        await asyncio.sleep(1)
        return "..."