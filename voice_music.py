from youtubesearchpython.__future__ import VideosSearch

import logging
import discord
from yt_dlp import YoutubeDL
import config

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ytdl = YoutubeDL(ytdl_format_options)


async def from_url(url):
    data = ytdl.extract_info(url, download=False)
    return data["url"]


async def play_music(query, mixer):
    try:
        response = await VideosSearch(query, limit=1, timeout=config.requests_timeout).next()
        if not response["result"]:
            return "`Ничего не нашлось(`"
        video = response["result"][0]
        source = await from_url(video['link'])
        music = {"name": video["title"],
                 "duration": video["duration"],
                 "stream": discord.FFmpegPCMAudio(source, executable=config.ffmpeg_local_file, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")}
        mixer.add_music(music)
        return f'Включил трек - {video["title"]}'
    except Exception as e:
        # logging.error(f"play_music - {traceback.format_exc()}")
        logging.warning(f"play_music - {e}")
        return f"Не получилось включить музыку. Ошибка {e}"


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
            return "Очередь музыки пуста"
        return "\n".join(lines)
    except Exception as e:
        # logging.error(f"play_music - {traceback.format_exc()}")
        logging.warning(f"get_que - {e}")
        return f"Ошибка при получении очереди {e}"


async def off_music(mixer):
    try:
        if not mixer.music_que:
            return "Сейчас не играет никакая музыка."
        mixer.skip_music()
        return "Успешно выключил музыку."
    except Exception as e:
        logging.warning(f"off_music - {e}")
        return f"Не выключить музыку. Ошибка {e}"
