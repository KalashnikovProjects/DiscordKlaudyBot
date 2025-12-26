import audioop
import threading
from collections import deque

import discord

from klaudy.config import FRAME_SIZE
from klaudy.audio.pcm_source import MusicPCMSource, VoicePCMSource


class PCMMixer(discord.AudioSource):
    def __init__(self):
        self.music_queue: deque[MusicPCMSource] = deque()
        self.voice_queue = deque()
        self.lock = threading.Lock()

    def add_music(self, source: MusicPCMSource):
        with self.lock:
            self.music_queue.append(source)

    def get_music_que(self):
        return self.music_queue

    def skip_music(self):
        self.music_queue.popleft()

    def add_voice(self, source: VoicePCMSource):
        with self.lock:
            self.voice_queue.append(source)

    def read(self) -> bytes:
        with self.lock:
            music = self.music_queue[0] if self.music_queue else None
            voice = self.voice_queue[0] if self.voice_queue else None

        if voice:
            music_gain = 0.1
            voice_gain = 2.0
        else:
            music_gain = 0.25
            voice_gain = 1.0

        if music:
            music_pcm = audioop.mul(music.read(), 2, music_gain)
            if music.is_empty():
                with self.lock:
                    self.music_queue.popleft()
        else:
            music_pcm = b"\0" * FRAME_SIZE

        if voice:
            voice_pcm = audioop.mul(voice.read(), 2, voice_gain)

            mixed = audioop.add(music_pcm, voice_pcm, 2)

            if voice.pos >= len(voice.pcm):
                with self.lock:
                    self.voice_queue.popleft()

            return mixed

        return music_pcm

    def cleanup(self):
        self.music_queue.clear()
        self.voice_queue.clear()
