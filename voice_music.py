from youtubesearchpython.__future__ import VideosSearch

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


class NotPlayingError(Exception):
    pass


async def from_url(url):
    data = ytdl.extract_info(url, download=False)
    return data["url"]


async def play_music(query, mixer):
    response = await VideosSearch(query, limit=1, timeout=config.requests_timeout).next()
    if not response["result"]:
        return None
    video = response["result"][0]
    source = await from_url(video['link'])
    music = {"name": video["title"],
             "duration": video["duration"],
             "stream": discord.FFmpegPCMAudio(source, executable=config.ffmpeg_file,
                                              before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")}
    mixer.add_music(music)
    return video["title"]


async def off_music(mixer):
    if not mixer.music_que:
        raise NotPlayingError
    mixer.skip_music()
