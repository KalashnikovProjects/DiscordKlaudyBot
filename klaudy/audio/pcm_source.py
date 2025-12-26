import discord
import subprocess

from klaudy.config import FRAME_SIZE


class PCMSource(discord.AudioSource):
    def __init__(self, pcm: bytes):
        self.pcm = pcm
        self.pos = 0

    def read(self) -> bytes:
        chunk = self.pcm[self.pos:self.pos + FRAME_SIZE]
        self.pos += FRAME_SIZE
        return chunk.ljust(FRAME_SIZE, b"\0")

    def is_opus(self):
        return False


class MusicPCMSource(PCMSource):
    def __init__(self, url: str, name: str, duration):
        self.proc = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel", "quiet",
                "-i", url,
                "-f", "s16le",
                "-ar", "48000",
                "-ac", "2",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        self.name = name
        self.duration = duration
        self.have_data = True

    def read(self) -> bytes:
        data = self.proc.stdout.read(FRAME_SIZE)
        if not data:
            self.have_data = False
            return b"\0" * FRAME_SIZE
        return data.ljust(FRAME_SIZE, b"\0")

    def is_empty(self):
        return not self.have_data

    def cleanup(self):
        if self.proc:
            self.proc.kill()


class VoicePCMSource(PCMSource):
    def __init__(self, pcm: bytes):
        self.pcm = pcm
        self.pos = 0

    def read(self) -> bytes:
        chunk = self.pcm[self.pos:self.pos + FRAME_SIZE]
        self.pos += FRAME_SIZE
        return chunk.ljust(FRAME_SIZE, b"\0")