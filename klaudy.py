import asyncio
import logging
import discord
import config
from gpt import GPT
import re


class CustomFormatter(logging.Formatter):
    green = "\x1b[32;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    white = "\x1b[0m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s (%(filename)-12s:%(lineno)-4d) %(levelname)-8s %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
        "default": white + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS["default"])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_answer_history(message: discord.Message, count):
    """
    Получает цепочку ответов на сообщения как историю сообщений
    """
    res = [message]
    while len(res) <= count and res[-1].reference and res[-1].reference.resolved:
        res.append(res[-1].reference.resolved)
    return res


def normalize_history(history):
    res = []
    last = "model"
    for i in history:
        if i["role"] == last:
            res.append({"role": "model", "parts": [""]})
        last = i["role"]
        res.append(i)
    return res


async def get_images(message: discord.Message):
    images = []

    # Обработка вложенных изображений
    for attachment in message.attachments:
        if attachment.content_type in ("image/png", "image/jpeg", "image/heic", "image/heif", "image/webp"):
            image_bytes = await attachment.read()
            images.append({"mime_type": attachment.content_type, "data": image_bytes})
    return images


class BotEventHandler(discord.Client):
    def __init__(self):
        logger = logging.getLogger()
        logger.setLevel(config.log_level)
        console = logging.StreamHandler()
        logger.addHandler(console)
        console.setFormatter(CustomFormatter())
        self.NIK_re = re.compile(r"@[0-9a-zA-Z._]{3,}")
        self.gpt = GPT(self)

        intents = discord.Intents.all()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix=f"!{config.name}")

    async def on_ready(self):
        logging.info(f'Бот подключен к {len(self.guilds)} серверам. {self.user.name} стартует')
        await asyncio.gather(self.gpt.tts_que_progress())

    async def on_message(self, message: discord.message.Message):
        if message.author == self.user:
            return
        if not ("@&1175193886591819881" in message.content or
                self.user.mentioned_in(message) or
                message.content.startswith(f"!{config.name}")):
            return

        async with message.channel.typing():
            answer = await self.process_brain(message)
            if answer == "":
                return
            await message.channel.send(answer, reference=message, allowed_mentions=discord.AllowedMentions.all())

    async def convert_message_to_dict(self, mes: discord.Message):
        cont = mes.content
        mentions = mes.mentions
        for mention in mentions:
            cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")
        if mes.author == self.user:
            return {"role": "model", "parts": [cont]}
        return {"role": "user", "parts": [f"@{mes.author.name}: {cont}"]}

    def post_process_result(self, s, members):
        def convert_ping(m):
            ping_name = m.group(0)[1:]
            if ping_name not in members:
                return f"@{ping_name}"
            return f"<@{members[ping_name].id}>"

        res = re.sub(self.NIK_re, convert_ping, s)
        if len(res) >= 2000:
            res = res[:1995] + "..."
        return res

    async def process_brain(self, message: discord.Message):
        history = get_answer_history(message, config.message_history)  # message.channel.history(limit=5)
        count = 0
        info_message = f"""[СИСТЕМНАЯ ИНФОРМАЦИЯ] Информация о чате
        Название сервера: {message.guild.name}
        Название канала: {message.channel}"""
        if len(message.guild.members) < 12:
            info_message += f"  Список ников пользователей чата: "
            for member in message.guild.members:
                info_message += f"  {member.display_name}: {member.name}"

        system_messages = [{"role": "user", "parts": [f"{config.klaudy_knowns}\n{info_message}"]},]

        images = await get_images(message)
        members = {member.name: member for member in message.guild.members}

        if not images:
            messages = []
            for mes in history:
                count += len(mes.content)
                if count > config.max_input_symbols:
                    break
                messages.append(await self.convert_message_to_dict(mes))
            if messages[-1]["role"] == "user":
                messages.append({"role": "model", "parts": ["ок"]})
            messages = system_messages + messages[::-1]
            messages = normalize_history(messages)
            chat_answer = await self.gpt.generate_answer(messages, members=members,
                                                         mes=message)
        else:
            new_text = f"{system_messages[0]['parts'][0]} \n {system_messages[-1]['parts'][0]}"
            messages = [{"role": "user", "parts": [{"text": new_text}, {"inline_data": images[0]}]}]
            chat_answer = await self.gpt.generate_image_answer(messages)
        res = self.post_process_result(chat_answer, members)
        return res


def main():
    bot = BotEventHandler()
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
