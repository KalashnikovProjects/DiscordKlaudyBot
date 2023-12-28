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
        await asyncio.gather(self.gpt.que_progress(), self.gpt.tts_que_progress())

    async def on_message(self, message: discord.message.Message):
        if message.author == self.user:
            return
        if ("@&1175193886591819881" in message.content or
                self.user.mentioned_in(message) or
                message.content.startswith(f"!{config.name}")):
            async with message.channel.typing():
                answer = await self.process_brain(message)
                await message.channel.send(answer, reference=message, allowed_mentions=discord.AllowedMentions.all())

    async def one_message_process(self, mes):
        cont = mes.content
        mentions = mes.mentions
        for mention in mentions:
            cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")
        if mes.author == self.user:
            return {"role": "assistant", "content": cont}
        return {"role": "user", "name": str(mes.author.id), "content": f"@{mes.author.name}: {cont}"}

    def result_process(self, s, members):
        def convert_ping(m):
            ping_name = m.group(0)[1:]
            if ping_name not in members:
                return f"@{ping_name}"
            return f"<@{members[ping_name].id}>"

        res = re.sub(self.NIK_re, convert_ping, s)
        return res

    def answer_history(self, message: discord.Message, count):
        res = [message]
        while len(res) <= count and res[-1].reference and res[-1].reference.resolved:
            res.append(res[-1].reference.resolved)
        return res

    async def process_brain(self, message):
        history = self.answer_history(message, 7)  # message.channel.history(limit=5)
        count = 0
        info_message = f"""Информация о чате
        Название сервера: {message.guild.name}
        Название канала: {message.channel}"""
        if len(message.guild.members) < 12:
            info_message += f"\nСписок ников пользователей чата: "
            for member in message.guild.members:
                info_message += f"\n{member.display_name}: {member.name}"

        system_messages = [{"role": "system", "content": config.clyde_knowns},
                           {"role": "system", "content": info_message}]

        messages = []
        for mes in history:
            count += len(mes.content)
            if count > 7000:
                break
            messages.append(await self.one_message_process(mes))
        system_messages.extend(messages[::-1])
        messages = system_messages
        members = {member.name: member for member in message.guild.members}
        chat_answer = await self.gpt.chat_gpt(messages, members=members,
                                              mes=message)
        res = self.result_process(chat_answer, members)
        return res


def main():
    bot = BotEventHandler()
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
