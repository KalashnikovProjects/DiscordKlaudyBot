import asyncio
import datetime
import io
import logging
import threading
from pydub import AudioSegment
import discord
from discord.ext import voice_recv
import speech_recognition as sr

import config
import mixer
import utils

recognizer = sr.Recognizer()
recognizer.operation_timeout = 60


class VoiceConnect:
    def __init__(self, vch: discord.VoiceChannel, gpt_obj, vc=None):
        self.saying = False
        self.vc: voice_recv.VoiceRecvClient = None
        self.mixer_player: mixer.MixerSourceQue = None
        self.users_recording_states = {}
        self.users_frames = {}
        self.connected = False
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
        if now - record_state["last_package_time"] > datetime.timedelta(seconds=1) and len(
                self.users_frames[user]) <= 40:
            self.users_frames[user] = []
        self.users_frames[user].append(data.pcm)

        record_state["last_package_time"] = now

    async def enter_voice(self, vch: discord.VoiceChannel, vc=None):
        if not vc:
            self.vc = await vch.connect(cls=voice_recv.VoiceRecvClient)
        else:
            self.vc = vc
        self.connected = True
        self.mixer_player = mixer.MixerSourceQue()
        threading.Thread(self.vc.play(self.mixer_player))
        utils.run_in_thread(self.check_states_loop())
        threading.Thread(self.vc.listen(voice_recv.BasicSink(self.process_callback)))

    async def check_states_loop(self):
        while self.connected:
            await asyncio.sleep(0.05)
            try:
                if not self.vc.is_connected():
                    await self.exit()
                    return
                await asyncio.sleep(0.1)
                if len(self.vch.members) <= 1:
                    await self.exit()
                    return
                for user, state in self.users_recording_states.items():
                    if len(self.users_frames[user]) > 40 and datetime.datetime.now() - state["last_package_time"] > datetime.timedelta(seconds=1):

                        data = self.users_frames[user].copy()
                        self.users_frames[user] = []
                        self.users_recording_states[user] = {"last_package_time": datetime.datetime(2000, month=1, day=1)}
                        utils.run_in_thread(self.process_raw_frames(data, user))
            except Exception:
                continue

    async def exit(self):
        del self.gpt_obj.voice_connections[self.vch.guild.id]
        await self.vc.disconnect()

    async def process_raw_frames(self, frames, user):
        try:
            source = b''.join(frames)
            audio = AudioSegment(source, sample_width=2, frame_rate=48000, channels=2)
            with sr.AudioFile(audio.export(format="wav")) as source:
                audio_data_wav = recognizer.record(source)
            query = recognizer.recognize_wit(audio_data_wav, config.wit_token)
            logging.info(f"Распознанный текст: {query}")
            # if "клауди" not in query.lower():
            #     return

            res = await self.gpt_obj.voice_gpt(query, user, self.vch, self.vc)
            if not self.vc.is_connected():
                return
            logging.info(f"Результат текст: {res}")
            tts_file = await self.create_tts(res)
            audio_source = discord.FFmpegPCMAudio(io.BytesIO(tts_file), executable=config.ffmpeg_local_file, pipe=True)
            self.mixer_player.add_talk(audio_source)
        except sr.UnknownValueError:
            return
        except sr.RequestError as e:
            logging.warning(f"Ошибка {e} в Speech Recognition")

    async def create_tts(self, text):
        a = await self.gpt_obj.que_tts(input=text, model="tts-1", voice=config.clyde_voice, speed=0.85)
        return a.read()
