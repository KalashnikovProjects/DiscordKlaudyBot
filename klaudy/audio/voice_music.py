from ytSearch import VideosSearch

import logging
from yt_dlp import YoutubeDL

from .mixer import PCMMixer
from .pcm_source import MusicPCMSource

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


async def play_music(query, mixer: PCMMixer):
    response = await VideosSearch(query, limit=1).next()
    if not response["result"]:
        return None

    video = response["result"][0]
    url = await from_url(video["link"])
    logging.info(f"play_music {video['title']} - {video}")
    mixer.add_music(MusicPCMSource(url, video["title"], video.get("duration")))

    return video["title"]



async def off_music(mixer):
    if not mixer.music_queue:
        raise NotPlayingError
    mixer.skip_music()
