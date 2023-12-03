import asyncio
import datetime
import logging
import time
import discord
import discord.ext.voice_recv
import speech_recognition as sr
from discord.ext import voice_recv
from pydub import AudioSegment
import requests
import config

CHUNK = 1024
FORMAT = 8
CHANNELS = 1
RATE = 48000
PAUSE_SECONDS = 3
THRESHOLD = 1500
recognizer = sr.Recognizer()


class VoiceConnect:
    def __init__(self):
        self.vch: discord.VoiceChannel = None
        self.vc: voice_recv.VoiceRecvClient = None
        self.users_recording_states = None
        self.users_frames = None
        self.connected = False
        self.gpt_obj = None

    async def enter_voice(self, vch: discord.VoiceChannel, gpt_obj):
        self.gpt_obj = gpt_obj
        self.users_frames = {}
        self.users_recording_states = {}
        self.connected = True
        self.vch = vch

        def callback(user, data: voice_recv.VoiceData):
            ext_data = data.packet.extension_data.get(voice_recv.ExtensionID.audio_power)
            value = int.from_bytes(ext_data, 'big')
            power = 127-(value & 127)
            if user not in self.users_frames:
                self.users_recording_states[user] = {"recording": False,
                                                     "last_package_time": datetime.datetime(2000, month=1, day=1)}
                self.users_frames[user] = []
            if user not in self.users_recording_states:
                self.users_recording_states[user] = {"recording": False,
                                                     "last_package_time": datetime.datetime(2000, month=1, day=1)}

            record_state = self.users_recording_states[user]
            now = datetime.datetime.now()
            if not record_state["recording"]:
                if now - record_state["last_package_time"] > datetime.timedelta(seconds=1):
                    self.users_frames[user] = []
                self.users_frames[user].append(data.pcm)

            record_state["last_package_time"] = now

        self.vc = await vch.connect(cls=voice_recv.VoiceRecvClient)
        asyncio.create_task(self.check_states_loop())
        self.vc.listen(voice_recv.BasicSink(callback))

    async def check_states_loop(self):
        while self.connected:
            await asyncio.sleep(1)
            if len(self.vch.members) <= 1:
                await self.exit()
                return
            for user, state in self.users_recording_states.items():
                if (len(self.users_frames[user]) > 40 and datetime.datetime.now() -
                        state["last_package_time"] > datetime.timedelta(seconds=1)):
                    state["recording"] = False
                    await self.process_raw_frames(self.users_frames[user], user)
                    self.users_frames[user] = []

    async def exit(self):
        await self.vc.disconnect()

    async def process_raw_frames(self, frames, user):
        source = b''.join(frames)
        audio = AudioSegment(source, sample_width=2, frame_rate=RATE, channels=2)

        audio.export("temp.wav", format="mp3")
        with sr.AudioFile(audio.export(format="wav")) as source:
            audio_data_wav = recognizer.record(source)
        try:
            query = recognizer.recognize_google(audio_data_wav, language='ru-RU')
            logging.debug(f"Распознанный текст: {query}")
            res = await self.gpt_obj.voice_gpt(query, user, self.vch, self.vc)
            # tts = gTTS(text, lang="ru")
            # tts.save('temp.mp3')
            audio_source = discord.FFmpegPCMAudio(await self.create_tts(res), executable="./ffmpeg.exe")
            while self.vc.is_playing():
                time.sleep(2)
            self.vc.play(audio_source)
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            logging.warning(f"Ошибка {e} в Google Speech Recognition")

    async def create_tts(self, text):
        a = await self.gpt_obj.que_tts(input=text, model="tts-1", voice=config.clyde_voice)
        a.stream_to_file("temp.mp3")
        return "temp.mp3"


