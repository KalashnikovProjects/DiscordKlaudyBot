# import traceback
import logging

import discord
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch

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
        video = YoutubeSearch(query, max_results=1).to_dict()[0]
        source = await from_url(f"https://www.youtube.com/watch?v={video['id']}")
        mixer.add_music(discord.FFmpegPCMAudio(source, executable=config.ffmpeg_local_file, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"))
        return f'`Включил трек - {video["title"]}`'
    except Exception as e:
        # traceback.print_exc()
        logging.warning(e)
        return f"Не получилось включить музыку. Ошибка {e}"


async def off_music(mixer):
    try:
        if not mixer.music_que:
            return "Сейчас не играет никакая музыка."
        mixer.skip_music()
        return "Успешно выключил музыку."
    except Exception as e:
        logging.warning(e)
        return f"Не получилось выключить музыку. Ошибка {e}"