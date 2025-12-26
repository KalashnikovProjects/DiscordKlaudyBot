import asyncio

import discord
from discord.ext import voice_recv, tasks

from klaudy import config
from . import mixer
from klaudy.gpt.gpt_voice import VoiceGPTClient
from .pcm_source import VoicePCMSource
from .voice_connections import VoiceConnections
from klaudy.audio.audio_utils import pcm24k_mono_to_pcm48k_stereo, pcm48k_stereo_to_pcm16k_mono


class VoiceConnect:
    def __init__(self, bot_user_id: int, voice_channel: discord.VoiceChannel, voice_connections: VoiceConnections, voice_connection=None):
        self.voice_gpt_client: VoiceGPTClient | None = None
        self.bot_user_id = bot_user_id
        self.voice_channel = voice_channel
        self.voice_connection: voice_recv.VoiceRecvClient = voice_connection
        self.voice_connections = voice_connections
        self.mixer_player: mixer.PCMMixer | None = None

    def generate_voice_info(self):
        chat_info = f"""Информация о голосовом канале \nНазвание сервера: {self.voice_channel.guild.name} \nНазвание канала: {self.voice_channel.name} \nСписок участников на сервере:"""
        if len(self.voice_channel.guild.members) < config.BotConfig.members_info_limit:
            for member in self.voice_channel.guild.members:
                chat_info += f" {member.display_name}: {member.name};"
        return chat_info

    @classmethod
    async def create(cls, bot_user_id: int, voice_channel: discord.VoiceChannel, voice_connections: VoiceConnections, voice_connection=None):
        instance = cls(bot_user_id, voice_channel, voice_connections, voice_connection)

        await instance.connect()
        return instance

    def voice_data_callback(self, user: discord.User, data: voice_recv.VoiceData):
        if user is None or user.id == self.bot_user_id:
            return

        asyncio.run_coroutine_threadsafe(
                self.voice_gpt_client.send(pcm48k_stereo_to_pcm16k_mono(data.pcm)),
                self.voice_gpt_client.loop
        )

    @tasks.loop(seconds=1)
    async def is_connected_watchdog(self):
        if not self.voice_connection or not self.voice_connection.is_connected() or len(self.voice_channel.members) <= 1:
            await self.exit()

    def process_output(self, data: bytes):
        pcm48k = pcm24k_mono_to_pcm48k_stereo(data)
        self.mixer_player.add_voice(VoicePCMSource(pcm48k))

    async def connect(self):
        if not self.voice_connection:
            self.voice_connection = await self.voice_channel.connect(
                cls=voice_recv.VoiceRecvClient
            )

        self.mixer_player = mixer.PCMMixer()

        self.voice_gpt_client = await VoiceGPTClient.new_session(
            self.mixer_player,
            output_callback=self.process_output,
            additional_info=""
        )

        self.voice_connection.play(self.mixer_player)
        self.voice_connection.listen(
            voice_recv.BasicSink(self.voice_data_callback)
        )

        self.is_connected_watchdog.start()

    async def move_to_channel(self, channel: discord.VoiceChannel):
        await self.voice_connection.move_to(channel)

    async def exit(self):
        self.voice_connections.remove_connection(self.voice_channel.guild.id)
        await self.voice_gpt_client.disconnect()
        await self.voice_connection.disconnect()
