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


async def get_images(message: discord.Message):
    images = []

    # Обработка вложенных изображений
    for attachment in message.attachments:
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

    async def convert_message_to_dict(self, mes: discord.Message, with_images=False):
        cont = mes.content
        mentions = mes.mentions
        for mention in mentions:
            cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")
        if mes.author == self.user:
            res = {"role": "model", "parts": [{"text": cont}]}
        else:
            res = {"role": "user", "parts": [{"text": f"@{mes.author.name}: {cont}"}]}
        if with_images:
            images = await get_images(mes)
            if images:
                res["parts"].append({"inline_data": images[0]})
        return res

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
        history = await get_answer_history(message, config.message_history)  # message.channel.history(limit=5)
        count = 0
        info_message = f"""[СИСТЕМНАЯ ИНФОРМАЦИЯ] Информация о чате
        Название сервера: {message.guild.name}
        Название канала: {message.channel}"""
        if len(message.guild.members) < 30:
            info_message += f"  Список ников пользователей чата: "
            for member in message.guild.members:
                info_message += f"{member.display_name}: {member.name}"

        system_message = f"{config.klaudy_knowns}\n{info_message}"

        images = await get_images(message)
        members = {member.name: member for member in message.guild.members}

        messages = []
        for mes in history:
            count += len(mes.content)
            if count > config.max_input_symbols:
                break
            messages.append(await self.convert_message_to_dict(mes, len(images) != 0))
        messages = messages[::-1]
        messages.insert(0, {"role": "user", "parts": [{"text": system_message}]})
        messages = normalize_history(messages)

        # info = None
        # if not images:
        #     messages.insert(0, {"role": "user", "parts": [{"text": system_message}]})
        #     messages = normalize_history(messages)
        # else:
        #     if messages[0]["role"] == "model":
        #         messages.pop(0)
        #     messages = normalize_history(messages)
        #     info = system_message

        chat_answer = await self.gpt.generate_answer(messages, images=len(images) != 0, members=members, mes=message)
        res = self.post_process_result(chat_answer, members)
        return res


def main():
    bot = BotEventHandler()
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
