import asyncio
import logging
from logging import debug, info, warning, error, critical
import discord
from discord.ext import commands
import config
from gpt import GPT
# from keep_alive import keep_alive
# keep_alive()


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


logger = logging.getLogger()
logger.setLevel(config.log_level)
console = logging.StreamHandler()
logger.addHandler(console)
console.setFormatter(CustomFormatter())

intents = discord.Intents.all()
intents.message_content = True
name = config.name
bot = commands.Bot(command_prefix=f"!{name}", intents=intents)


async def one_message_process(mes):
    cont = mes.content
    mentions = mes.mentions
    for mention in mentions:
        cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")

    # res_name = mes.author.name.replace('.', '-')
    # if not re.match(kirillic_re, res_name):
    #     res_name = "discord_bot"
    if mes.author == bot.user:
        return {"role": "assistant", "content": cont}
    return {"role": "user", "name": str(mes.author.id), "content": f"@{mes.author.name}: {cont}"}


async def process_brain(message):
    history = message.channel.history(limit=5)
    count = 0
    info_message = f"""Информация о чате
    Название сервера: {message.guild.name}
    Название канала: {message.channel}"""
    if len(message.guild.members) < 12:
        info_message += f"\nСписок ников пользователей чата: "
        for member in message.guild.members:
            info_message += f"\n{member.display_name}: {member.name}"

    system_messages = [{"role": "system", "content": config.clyde_knowns}, {"role": "system", "content": info_message}]

    messages = []
    async for mes in history:
        # if len(mes.content) > 1900:
        #     mes.content = mes.content[-1900:]
        count += len(mes.content)
        if count > 7000:
            break
        messages.append(await one_message_process(mes))
    system_messages.extend(messages[::-1])
    messages = system_messages
    chat_answer = await gpt.chat_gpt(messages, members={member.name: member for member in message.guild.members}, mes=message)

    return chat_answer


@bot.event
async def on_ready():
    info(f'Бот подключен к {len(bot.guilds)} серверам. {bot.user.name} стартует')
    await asyncio.gather(gpt.que_progress(), gpt.tts_que_progress())


@bot.event
async def on_message(message: discord.message.Message):
    if message.author == bot.user:
        return
    if "@&1175193886591819881" in message.content or bot.user.mentioned_in(message) or message.content.startswith(
            bot.command_prefix):
        async with message.channel.typing():
            answer = await process_brain(message)
            await message.channel.send(answer, reference=message, allowed_mentions=discord.AllowedMentions.all())

    await bot.process_commands(message)


if __name__ == "__main__":
    gpt = GPT()
    bot.run(config.discord_token)
