import asyncio
import datetime
import logging
import threading
import io

import discord
from discord.ext import voice_recv
from pydub import AudioSegment
import elevenlabs
from elevenlabs.client import ElevenLabs

"""
Библиотека для расширения voice_recv работает только с нерелизнутой версией discord.py с github
(discord.py 2.4+)
"""

from . import config
from . import mixer
from . import utils


def write_iterator_to_stream(stream, iterator) -> io.BytesIO:
    for chunk in iterator:
        stream.write(chunk)
    return stream


class GenerateAudioStreamWithRead20ms:
    def __init__(self, audio_bytes_io, sample_rate, bit_depth=16, channels=1):
        self.audio_bytes_io = audio_bytes_io
        bytes_per_second = (sample_rate * bit_depth * channels) // 8
        self.chunk_size = (bytes_per_second * 20) // 1000

    def write(self, chunk):
        self.audio_bytes_io.write(chunk)
        logging.debug(f"Записал чанк в поток: {chunk}")

    def read(self):
        self.audio_bytes_io.seek(0)
        res = self.audio_bytes_io.read(self.chunk_size)
        logging.debug(f"Читаю аудио из потока: {res}")
        return res

    def clean_up(self):
        ...
        self.audio_bytes_io.close()


class VoiceConnect:
    def __init__(self, vch: discord.VoiceChannel, gpt_obj, vc=None):
        self.saying = False
        self.vc: voice_recv.VoiceRecvClient = None
        self.mixer_player: mixer.MixerSourceQue = None
        self.users_recording_states = {}
        self.users_frames = {}
        self.vch = vch
        self.gpt_obj = gpt_obj
        utils.run_in_thread(self.enter_voice(vch, vc=vc))

    def process_callback(self, user, data: voice_recv.VoiceData):
        if user is None or user == self.gpt_obj.bot.user:
            return
        if user not in self.users_frames:
            self.users_recording_states[user] = {"last_package_time": datetime.datetime(2000, month=1, day=1)}
            self.users_frames[user] = []
        if user not in self.users_recording_states:
            self.users_recording_states[user] = {"last_package_time": datetime.datetime(2000, month=1, day=1)}

        record_state = self.users_recording_states[user]
        now = datetime.datetime.now()
        if now - record_state["last_package_time"] > datetime.timedelta(seconds=2.5) and len(
                self.users_frames[user]) <= 30:
            self.users_frames[user] = []
        self.users_frames[user].append(data.pcm)

        record_state["last_package_time"] = now

    async def enter_voice(self, vch: discord.VoiceChannel, vc=None):
        if not vc:
            self.vc = await vch.connect(cls=voice_recv.VoiceRecvClient)
        else:
            self.vc = vc
        self.mixer_player = mixer.MixerSourceQue()
        threading.Thread(self.vc.play(self.mixer_player))
        utils.run_in_thread(self.check_states_loop())
        threading.Thread(self.vc.listen(voice_recv.BasicSink(self.process_callback)))

    async def check_states_loop(self):
        while self.vc and self.vc.is_connected():
            await asyncio.sleep(0.05)
            try:
                await asyncio.sleep(0.1)
                if not self.vch or len(self.vch.members) <= 1:
                    break
                for user, state in self.users_recording_states.items():
                    if len(self.users_frames[user]) > 30 and datetime.datetime.now() - state[
                            "last_package_time"] > datetime.timedelta(seconds=2.5):
                        data = self.users_frames[user].copy()
                        self.users_frames[user] = []
                        self.users_recording_states[user] = {
                            "last_package_time": datetime.datetime(2000, month=1, day=1)}
                        utils.run_in_thread(self.process_raw_frames(data, user))
            except Exception as e:
                logging.debug(f"Ошибка {e} при обработке frame'ов.")
                continue
        await self.exit()

    async def exit(self):
        self.gpt_obj.voice_connections.pop(self.vch.guild.id)
        await self.vc.disconnect()

    async def process_raw_frames(self, frames, user):
        try:
            source = b''.join(frames)
            audio = AudioSegment(source, sample_width=2, frame_rate=48000, channels=2).export(format="wav").read()
            logging.info("Аудио отправляется")
            text = await self.gpt_obj.generate_answer_for_voice(audio, user, self.vch)
            if not self.vc.is_connected():
                return
            speech_bytes_iterator = await self.create_tts(text)

            speech_stream = io.BytesIO()
            audio_stream_source = GenerateAudioStreamWithRead20ms(speech_stream, 22050, 16, 1)
            write_iterator_to_stream(audio_stream_source, speech_bytes_iterator)
            # threading.Thread(target=write_iterator_to_stream, args=(audio_stream_source, speech_bytes_iterator))
            self.mixer_player.add_talk({"author": config.BotConfig.name, "stream": audio_stream_source})

            # speech_bytes = io.BytesIO()
            # for speech_bytes_it in speech_bytes_iterator:
            #     speech_bytes.write(speech_bytes_it)
            # audio_source = discord.FFmpegPCMAudio(speech_bytes, executable=config.FFMPEG_FILE, pipe=True)
            # self.mixer_player.add_talk({"author": config.BotConfig.name, "stream": audio_source})
        except Exception as e:
            logging.warning(f"Ошибка {e} в в process_raw_frames")

    # @utils.api_rate_limiter_with_ques(rate_limit=config.ElevenLabs.rate_limit, tokens=config.ElevenLabs.tokens)
    async def create_tts(self, text, token=config.ElevenLabs.token):
        client = ElevenLabs(api_key=token)

        result = client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=config.ElevenLabs.voice_id,
            voice_settings=elevenlabs.VoiceSettings(stability=0.5, similarity_boost=0.6),
        )
        return result
