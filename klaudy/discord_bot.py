import logging
import discord
import re

from . import config
from .gpt import GPT, upload_file


async def get_answer_history(message: discord.Message, count):
    """
    Получает цепочку ответов на сообщения как историю сообщений
    """
    res = [message]
    messages_cache = {i.id: i async for i in message.channel.history(limit=count * 4)}
    while len(res) <= count and res[-1].reference and res[-1].reference.message_id:
        m = messages_cache.get(res[-1].reference.message_id)
        if m:
            res.append(m)
        else:
            break
    return res


def normalize_history(history):
    res = []
    last = "model"
    for i in history:
        if i["role"] == last:
            res.append({"role": "model", "parts": [{"text": ""}]})
        last = i["role"]
        res.append(i)
    return res


async def get_files(message: discord.Message):
    inline_data = []
    file_data = []
    need_upload = any([(i.size / 1024 / 1024 > 19 or i.content_type.split("/")[0] == "video") for i in message.attachments if i.content_type])

    for attachment in message.attachments:
        data = await attachment.read()

        if need_upload:
            uri = await upload_file(data, attachment.content_type, attachment.filename)
            file_data.append({"mime_type": attachment.content_type, "file_uri": uri})
        else:
            inline_data.append({"mime_type": attachment.content_type, "data": data})
    return inline_data, file_data


def generate_chat_info(message: discord.Message):
    chat_info = f"""Информация о чате \nНазвание сервера: {message.guild.name} \nНазвание канала: {message.channel} \nСписок пользователей чата: """
    if len(message.guild.members) < config.BotConfig.members_info_limit:
        chat_info += f""
        for member in message.guild.members:
            chat_info += f" {member.display_name}: {member.name};"
    return chat_info


def get_members(message: discord.Message):
    return {member.name: member for member in message.guild.members}


class BotEventHandler(discord.Client):
    def __init__(self):
        self.NIK_re = re.compile(r"@[0-9a-zA-Z._]{3,}")
        self.gpt = GPT(self)

        intents = discord.Intents.all()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix=f"!{config.BotConfig.name}")

    async def on_ready(self):
        logging.info(f'Бот подключен к {len(self.guilds)} серверам. {self.user.name} стартует')

    async def on_message(self, message: discord.message.Message):
        if message.author == self.user:
            return
        if not ("@&1175193886591819881" in message.content or
                self.user.mentioned_in(message) or
                message.content.startswith(f"!{config.BotConfig.name}")):
            return

        async with message.channel.typing():
            answer = await self.process_brain(message)
            if answer == "":
                return
        await message.channel.send(answer, reference=message, allowed_mentions=discord.AllowedMentions(users=True, replied_user=True))

    async def process_brain(self, message: discord.Message):
        chat_info = generate_chat_info(message)

        history = await get_answer_history(message, config.BotConfig.message_history)  # message.channel.history(limit=5)
        messages = await self.convert_history_to_messages(history, config.BotConfig.max_input_symbols, config.BotConfig.file_history)
        members = get_members(message)

        chat_answer = await self.gpt.generate_answer(messages, members=members, mes=message, additional_info=chat_info)
        res = self.convert_ai_answer_to_message_text(chat_answer, members)
        return res

    async def convert_history_to_messages(self, history, max_input_symbols, file_history):
        messages = []
        count = 0

        for n, mes in enumerate(history):
            count += len(mes.content)
            if count > max_input_symbols:
                break
            messages.append(await self.convert_message_to_dict(mes, with_files=n <= file_history))
        messages = messages[::-1]
        messages = normalize_history(messages)
        return messages

    async def convert_message_to_dict(self, mes: discord.Message, with_files=False):
        cont = mes.content
        mentions = mes.mentions
        for mention in mentions:
            cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")
        if mes.author == self.user:
            res = {"role": "model", "parts": [{"text": cont}]}
        else:
            res = {"role": "user", "parts": [{"text": f"@{mes.author.name}: {cont}"}]}
        if with_files:
            inline_data, file_data = await get_files(mes)
            if inline_data:
                res["parts"].extend([{"inline_data": image} for image in inline_data])
            if file_data:
                res["parts"].extend([{"file_data": image} for image in file_data])
        return res

    def convert_ai_answer_to_message_text(self, s, members):
        def convert_ping(m):
            ping_name = m.group(0)[1:]
            if ping_name not in members:
                return f"@{ping_name}"
            return f"<@{members[ping_name].id}>"

        res = re.sub(self.NIK_re, convert_ping, s)
        if len(res) >= 2000:
            res = res[:1995] + "..."
        return res


def run_bot():
    bot = BotEventHandler()
    bot.run(config.Discord.token)
