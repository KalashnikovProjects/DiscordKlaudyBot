from dataclasses import dataclass

import discord
import re

from discord import Member

from . import config

NIK_RE = re.compile(r"@[0-9a-zA-Z._]{3,}")


@dataclass
class DataForGeneration:
    messages: list[dict]
    members: dict[str, Member]
    chat_info: str

async def extract_data_from_messages(bot_user_id: int, message: discord.Message) -> DataForGeneration:
    history = await get_answer_history(message, config.BotConfig.message_history)  # message.channel.history(limit=5)

    messages = await convert_history_to_messages(bot_user_id, history, config.BotConfig.max_input_symbols,
                                                           config.BotConfig.file_history)
    chat_info = generate_chat_info(message)
    members = get_members(message)
    return DataForGeneration(messages=messages, chat_info=chat_info, members=members)

async def get_answer_history(message: discord.Message, count):
    """
    Получает цепочку ответов на сообщения как историю сообщений
    """
    res = [message]
    messages_cache = {i.id: i async for i in message.channel.history(limit=count * 4)}
    while len(res) <= count and res[-1].reference and res[-1].reference.message_id:
        mes = messages_cache.get(res[-1].reference.message_id)
        if mes:
            res.append(mes)
        else:
            break
    return res


def normalize_history(history):
    res = []
    last = "assistant"
    for i in history:
        if i["role"] == last:
            res.append({"role": "assistant" if i["role"] == "user" else "user", "parts": [{"text": "."}]})
        res.append(i)
        last = i["role"]
    return res


def generate_chat_info(message: discord.Message):
    if message.guild:
        chat_info = f"""Информация о чате \nНазвание сервера: {message.guild.name} \nНазвание канала: {message.channel.name} \nСписок пользователей чата:"""
        if len(message.guild.members) < config.BotConfig.members_info_limit:
            for member in message.guild.members:
                chat_info += f"Отображемый ник: {member.display_name}, уникальный ник: {member.name}\n"
    else:
        chat_info = f"Ты сейчас в личных сообщениях с пользователем {message.author.display_name}: {message.author.name}"
    return chat_info


def get_members(message: discord.Message):
    if message.guild:
        return {member.name: member for member in message.guild.members}
    else:
        return {message.author.name: message.author}


async def convert_message_to_dict(bot_user_id: int, mes: discord.Message, with_files=False):
    cont = mes.content
    mentions = mes.mentions
    for mention in mentions:
        cont = cont.replace(f"<@{mention.id}>", f"@{mention.name}")
    if mes.author.id == bot_user_id:
        res = {"role": "assistant", "content": [{"type": "text", "text": cont}]}
    else:
        res = {"role": "user", "content": [{"type": "text", "text": f"@{mes.author.name}: {cont}"}]}
    if with_files:
        for attachment in mes.attachments:
            if attachment.content_type.split("/")[0] == "image":
                image = attachment.url
                res["content"].append({"type": "image_url", "image_url": image})
    return res


def convert_ai_answer_to_message_text(s: str, members: dict[str, Member]) -> str:
    def convert_ping(m):
        ping_name = m.group(0)[1:]
        if ping_name in members:
            return f"<@{members[ping_name].id}>"
        if ping_name[-1] == "." and ping_name[:-1] in members:
            return f"<@{members[ping_name[:-1]].id}>."
        return f"@{ping_name}"


    res = re.sub(NIK_RE, convert_ping, s)
    return res

async def convert_history_to_messages(bot_user_id, history, max_input_symbols, file_history) -> list[dict]:
    messages = []
    count = 0

    for n, mes in enumerate(history):
        count += len(mes.content)
        if count > max_input_symbols:
            break
        messages.append(await convert_message_to_dict(bot_user_id=bot_user_id, mes=mes, with_files=n <= file_history))
    messages = messages[::-1]
    return messages


# Split by \n or space to strings <2000 symbols len
def split_text(text, max_len):
    parts = []

    while len(text) > max_len:
        chunk = text[:max_len]

        split_pos = chunk.rfind('\n')

        if split_pos == -1:
            split_pos = chunk.rfind(' ')

        if split_pos == -1:
            split_pos = max_len

        parts.append(text[:split_pos].rstrip())
        text = text[split_pos:].lstrip()

    if text:
        parts.append(text)

    return parts
