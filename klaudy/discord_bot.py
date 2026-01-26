import logging
from typing import  AsyncGenerator

import discord
import re

from . import config, message_convertor
from klaudy.audio.voice_connections import VoiceConnections
from klaudy.gpt.gpt_text import TextGPT


class BotEventHandler(discord.Client):
    def __init__(self):
        self.NIK_re = re.compile(r"@[0-9a-zA-Z._]{3,}")
        self.text_gpt = TextGPT()
        self.voice_connections = VoiceConnections()

        intents = discord.Intents.all()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix=f"!{config.BotConfig.name}")

    async def on_ready(self):
        logging.info(f'Бот подключен к {len(self.guilds)} серверам. {self.user.name} стартует')

    async def bot_pinged(self, message: discord.Message):
        if message.author == self.user:
            return False
        if not message.guild:
            return True
        if self.user.mentioned_in(message) or message.content.startswith(f"!{config.BotConfig.name}"):
            return True
        roles = message.guild.get_member(self.user.id).roles
        for role in roles:
            if f"<@&{role.id}>" in message.content:
                return True

    async def on_message(self, message: discord.message.Message):
        if not await self.bot_pinged(message):
            return

        async with message.channel.typing():
            last_message: discord.Message | None = None
            async for part in self.process_brain_parts(message):
                if part == "":
                    continue
                last_message = await message.channel.send(part, reference=message if not last_message else last_message,
                                                          allowed_mentions=discord.AllowedMentions(users=True,
                                                                                                   replied_user=True))


    async def process_brain_parts(self, message: discord.Message) -> AsyncGenerator[str]:
        data = await message_convertor.extract_data_from_messages(self.user.id, message)
        async for part in self.text_gpt.generate_answer_parts(messages_history=data.messages,
                                                              mes=message,
                                                              members=data.members,
                                                              bot_user_id=self.user.id,
                                                              voice_connections=self.voice_connections,
                                                              additional_info=data.chat_info,
                                                              is_pm=message.guild is None):
            text = message_convertor.convert_ai_answer_to_message_text(part, data.members)
            for text_part in message_convertor.split_text(text, config.Discord.max_output_symbols):
                yield text_part


def run_bot():
    bot = BotEventHandler()
    bot.run(config.Discord.token)
