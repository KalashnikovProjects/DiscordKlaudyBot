from youtubesearchpython.__future__ import VideosSearch

import logging
import discord
from yt_dlp import YoutubeDL

from . import config

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


class NotPlayingError(Exception):
    pass


async def from_url(url):
    data = ytdl.extract_info(url, download=False)
    # logging.debug(f"from_url {data['url']} - {data}")
    return data["url"]


async def play_music(query, mixer):
    response = await VideosSearch(query, limit=1, timeout=config.REQUESTS_TIMEOUT).next()
    if not response["result"]:
        logging.warning(f"play_music no result - {response}")
        return None
    video = response["result"][0]
    source = await from_url(video['link'])
    music = {"name": video["title"],
             "duration": video["duration"],
             "stream": discord.FFmpegPCMAudio(source, executable=config.FFMPEG_FILE,
                                              before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")}
    logging.info(f"play_music {video['title']} - {video}")
    mixer.add_music(music)
    return video["title"]


async def off_music(mixer):
    if not mixer.music_que:
        raise NotPlayingError
    mixer.skip_music()
