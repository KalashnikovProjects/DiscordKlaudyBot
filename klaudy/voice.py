import asyncio
import datetime
import io
import logging
import threading

import discord
from aiogtts import aiogTTS
from discord.ext import voice_recv
from pydub import AudioSegment
from pydub.effects import speedup

from . import config
from . import mixer
from . import utils


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
            tts_bytes = await self.create_tts(text)
            pitched_audio = speedup((await self.change_voice_pitch(AudioSegment.from_file(tts_bytes), 2)), 1.2)
            audio_source = discord.FFmpegPCMAudio(pitched_audio.export(format="wav"), executable=config.FFMPEG_FILE, pipe=True)
            self.mixer_player.add_talk({"author": config.BotConfig.name, "stream": audio_source})
        except Exception as e:
            logging.warning(f"Ошибка {e} в в process_raw_frames")

    async def create_tts(self, text):
        aiogtts = aiogTTS()
        bytes_io = io.BytesIO()
        await aiogtts.write_to_fp(text, bytes_io, lang='ru')
        bytes_io.seek(0)
        return bytes_io

    async def change_voice_pitch(self, audio, semitones):
        new_sample_rate = int(audio.frame_rate * (2 ** (semitones / 12)))
        pitched_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
        return pitched_audio.set_frame_rate(audio.frame_rate)
