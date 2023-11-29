import asyncio
import json
import logging
import time
from logging import debug, info, warning, error, critical

import aiohttp
import discord
import html2text
import openai
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from discord.flags import flag_value
from openai import AsyncOpenAI

import config


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


@flag_value
def legacy_costil(s):
    return 1 << 15


discord.Intents.message_content = legacy_costil
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
intents.typing = True
intents.presences = True
name = config.name
bot = commands.Bot(command_prefix=f"!{name}", intents=intents)

# proxy_number = 0
model_number = 0
models_dead = False

openai_client = AsyncOpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=config.openai_token,
    base_url=config.chatgpt_server,
    max_retries=1
)
html2text_client = html2text.HTML2Text()
html2text_client.ignore_links = True
html2text_client.ignore_images = True
html2text_client.unicode_snob = True
html2text_client.decode_errors = 'replace'

openai_que = []
openai_message_count = 3


async def get_member_text(member):
    try:
        info_message = f"\nНик: {member.name} \nОтображаемое имя: \n{member.display_name} \nУпоминание(тег): {member.mention}"
        if member.activity:
            attrs = [
                ('Имя ', member.activity.name),
                ('детали', ""),
            ]
            try:
                attrs[1] = ("детали", member.activity.details)
            except Exception:
                pass
            inner = ' '.join(" - ".join(t) for t in attrs if t[1] is not None)
            info_message += f"\nАктивность: {inner}"
            types = ("Играет", "Стримит", "Слушает", "Смотрит", "Другое", "Соревнуется", "Неизвестно")
            if member.activity.type is not None and member.activity.type.value != -1:
                info_message += f" Тип активности - {types[member.activity.type.value]}"
        if member.bot:
            info_message += f"\nДанный пользователь является ботом."
        else:
            info_message += f"\nДанный пользователь не является ботом."
        return info_message
    except Exception as e:
        return f"Ошибка {e}"


async def get_member(nick, members):
    try:
        if nick == "discord_bot":
            return f"Пользователь является ботом дискорд."
        nick = nick.replace("-", ".")
        member = members.get(nick)
        if not member:
            return f"Пользователь {nick} не найден"
        return await get_member_text(member)
    except Exception as e:
        return f"Ошибка {e}"


async def voice(message):
    try:
        voice_channel = message.author.voice.channel
        voice_client = await voice_channel.connect()

        # source = discord.FFmpegPCMAudio(sound_file)
        # voice_client.play(source)

        while voice_client.is_playing():
            await asyncio.sleep(1)
    except Exception as e:
        return f"Ошибка {e}"


async def simple_link_checker(url):
    try:
        async with aiohttp.ClientSession() as aiohttp_session:
            async with aiohttp_session.get(url) as res:
                res.encoding = 'UTF-8'
                text = html2text_client.handle(await res.text())
                if len(text) > 2000:
                    text = text[:2000]
                return text
    except Exception as e:
        return f"Ошибка {e}"


async def link_checker(url):
    try:
        async with aiohttp.ClientSession() as aiohttp_session:
            async with await aiohttp_session.get(url) as res:
                res.encoding = 'UTF-8'
                text = html2text_client.handle(await res.text())
            if len(text) < 2500:
                if len(text) > 2000:
                    text = text[:1950] + "..."
                return text
            auth = f'OAuth {config.ya300_token}'
            async with await aiohttp_session.post(config.ya300_server, json={"article_url": url}, headers={"Authorization": auth}) as response:
                data = await response.json()

            if data["status"] != "success":
                text = text[:1950] + "..."
                return text
            async with aiohttp_session.get(data["sharing_url"]) as res:
                res.encoding = 'UTF-8'
                soup = BeautifulSoup(await res.text(), 'html.parser')

                # Находим все элементы, соответствующие селектору '.thesis-text span'
                res = f"{soup.select('h1.title')[0].text}\n"
                thesis_elements = soup.select('.thesis-text span')
                for i in thesis_elements:
                    if len(i.text) > 2:
                        res += f"{i.text}\n"

                if len(res) > 2000:
                    res = res[:1950] + '...'
                return res
    except Exception as e:
        return f"Ошибка {e}"


async def search_gif_on_tenor(query):
    try:
        api_key = config.tenor_token
        url = config.tenor_server

        params = {
            'q': query,
            'key': api_key,
            'limit': 1,
            'ckey': "my_test_app"
        }
        async with aiohttp.ClientSession() as aiohttp_session:
            async with aiohttp_session.get(url, params=params) as response:
                data = await response.json()
                gif_url = data['results'][0]['media_formats']["gif"]["url"]
                return gif_url
    except Exception as e:
        return f"Ошибка {e}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "search_gif_on_tenor",
            "description": "находит ссылку на gif (гифку) по любой теме с помощью Tenor",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Запрос, по которому нужно найти gif (обычно не более 5 слов)",
                    }},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "function": {
            "name": "link_checker",
            "description": "просматривает содержимое сайта, если на нём много текста напишет его краткий пересказ с помощью нейросети YandexGPT.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Ссылка на сайт или статью",
                    }},
            },
            "required": ["url"],
        },
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "get_member",
    #         "description": "получает информацию о пользователе по его никнейму (не по имени) (статус, отображаемое имя, его активность, является ли он ботом и его тег (упоминание)). Используй только если пользователь просит узнать о ком то информацию в своём сообщении и если это не ты.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "nick": {
    #                     "type": "string",
    #                     "description": "Ник пользователя, которого нужно найти, за ним нужно обратиться к списку ников участников",
    #                 }},
    #         },
    #         "required": ["nick"],
    #     },
    # }
]


async def timer_reset():
    await asyncio.sleep(60)
    global openai_message_count
    if openai_message_count != 3:
        openai_message_count += 1


async def que_gpt(**kwargs):
    global openai_que, openai_message_count

    if openai_que or openai_message_count == 0:
        my = time.time()
        openai_que.append(my)
        while my in openai_que:
            await asyncio.sleep(1)
    openai_message_count -= 1
    res = await openai_client.chat.completions.create(**kwargs)
    asyncio.create_task(timer_reset())
    return res


async def chat_gpt(messages, members={}):
    global models_dead, model_number
    # global proxy_number
    # proxy_number = (proxy_number + 1) % len(config.proxies)
    try:
        # json_data = {"model": config.model, "messages": messages,
        #              "tools": tools, "tool_choice": "auto"}
        # res = requests.aiohttp_session.post(config.chatgpt_server, json=json_data,
        #                     headers={"Authorization": f"Bearer {config.openai_token}"}, timeout=30)

        res = await que_gpt(
            messages=messages,
            model=config.models[model_number],
            tools=tools, tool_choice="auto",
        )
        await asyncio.sleep(0.1)
        resp_message = res.choices[0].message
        if resp_message.tool_calls:
            tool_calls = resp_message.tool_calls
            available_functions = {
                "search_gif_on_tenor": (search_gif_on_tenor, ("query",)),
                "link_checker": (link_checker, ("url",)),
                "get_member": (get_member, ("nick",))
            }
            messages.append(resp_message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                kwargs = {a: b for a, b in function_args.items() if a in function_to_call[1]}
                if function_name == "get_member":
                    kwargs["members"] = members
                function_response = await function_to_call[0](**kwargs)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
            res = await que_gpt(
                messages=messages,
                model=config.models[model_number]
            )
            resp_message = res.choices[0].message
        models_dead = False
        return resp_message.content
    except openai.RateLimitError as e:
        # warning(e.message, e.status_code)
        if "RPM" in e.message:
            return f"Произошёл минутный рейт лимит (3 запроса в минуту, подожди)"
        else:
            if models_dead:
                return f"Произошёл дневной рейт лимит (200 запросов в день)"
            models_dead = True
            model_number = (model_number + 1) % len(config.models)
            return await chat_gpt(messages)
    except openai.APITimeoutError:
        return f"Произошёл таймаут запроса (ошибка)"
    except Exception as e:
        return f"Ошибка {e}"


async def simple_chat_gpt(prompt):
    try:
        json_data = {"model": config.models[model_number], "messages": [{"role": "user", "content": prompt}]}
        async with aiohttp.ClientSession() as aiohttp_session:
            async with aiohttp_session.post(config.chatgpt_server, json=json_data,
                            headers={"Authorization": f"Bearer {config.openai_token}"}) as res:
                res = await res.json()
                return res["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Ошибка {e}"


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
    chat_answer = await chat_gpt(messages, members={member.name: member for member in message.guild.members})

    return chat_answer


@bot.event
async def on_ready():
    info(f'Бот подключен к {len(bot.guilds)} серверам. {bot.user.name} стартует')
    que_task = asyncio.create_task(que_progress())
    await que_task


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


async def que_progress():
    while True:
        sleep_count = min(len(openai_que), openai_message_count)
        for i in range(sleep_count):
            openai_que.pop(0)
            await asyncio.sleep(1.5)
        await asyncio.sleep(3)


if __name__ == "__main__":
    bot.run(config.discord_token)

