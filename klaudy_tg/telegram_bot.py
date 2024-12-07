import io
import logging
from collections import defaultdict
from typing import List, Dict, Any
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from dataclasses import dataclass
import telegramify_markdown
from pydub import AudioSegment

from . import config, utils
from .gpt import GPT, upload_file

telegramify_markdown.customize.strict_markdown = False
telegramify_markdown.customize.cite_expandable = True
telegramify_markdown.customize.latex_escape = True


def escape_markdown(text):
    escape_chars = ['[', ']', '(', ')', '~', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    return ''.join('\\' + char if char in escape_chars else char for char in text)


class BotAction:
    def __init__(self, bot, chat_id, action):
        self.action = action
        self.bot = bot
        self.chat_id = chat_id
        self.completed = False

    async def start(self):
        utils.run_in_thread(self.action_loop())

    async def __aenter__(self):
        await self.start()

    async def action_loop(self):
        while not self.completed:
            await self.bot.send_chat_action(self.chat_id, self.action)
            await asyncio.sleep(5)

    async def exit(self):
        self.completed = True

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exit()


@dataclass
class FileId:
    id: str
    mime_type: str | None


@dataclass
class CacheMessage:
    autor: str
    text: str
    files_uri: list[str]


def ogg_to_wav_bytes(ogg_bytes):
    ogg_audio = AudioSegment.from_ogg(io.BytesIO(ogg_bytes))
    wav_bytes = ogg_audio.export(format="wav").read()
    return wav_bytes


class MessagesCache:
    def __init__(self, limit=10):
        self.storage = defaultdict(list)
        self.limit = limit

    def clear_chat(self, chat_id: int):
        self.storage.pop(chat_id)

    def add(self, chat_id: int, message: CacheMessage):
        self.storage[chat_id].append(message)
        if len(self.storage[chat_id]) > self.limit:
            self.storage[chat_id].pop(0)

    def get(self, chat_id: int) -> list[CacheMessage]:
        return self.storage.get(chat_id, [])


class TelegramBot:
    def __init__(self):
        self.messages_cache = MessagesCache(limit=config.BotConfig.message_history)

        self.me = None
        self.bot = Bot(token=config.Telegram.token)
        self.dp = Dispatcher()
        self.gpt = GPT()
        self.setup_handlers()

    async def setup_me(self):
        self.me = await self.bot.get_me()

    async def get_message_files(self, message: Message):
        files = [FileId(id=i.file_id,
                        mime_type=i.mime_type if hasattr(i, 'mime_type') else None)
                 for i in (
                     message.document, message.video, message.audio, message.sticker, message.video_note)
                 if i and not (hasattr(i, 'is_animated') and i.is_animated or hasattr(i, 'is_video') and i.is_video)]
        if message.photo:
            files.extend([FileId(id=i.file_id, mime_type=None) for i in message.photo])
        if message.voice:
            files.append(FileId(id=message.voice.file_id, mime_type="ogg"))
        return files

    async def upload_files(self, files: list[FileId]) -> list[str]:
        file_data = []

        for i in files:
            data = (await self.bot.download_file((await self.bot.get_file(i.id)).file_path)).read()
            mime_type = i.mime_type
            if i.mime_type and "ogg" in i.mime_type:
                data = ogg_to_wav_bytes(data)
                mime_type = "audio/wav"
            uri = await upload_file(data, mime_type, i.id)
            file_data.append(uri)
        return file_data

    def setup_handlers(self):
        self.dp.message.register(self.handle_message)

    async def add_to_history(self, message: Message):
        files = await self.upload_files(await self.get_message_files(message))
        text = message.text or message.caption or ""

        mes = CacheMessage(autor=message.from_user.username, text=text, files_uri=files)
        self.messages_cache.add(message.chat.id, mes)

    async def load_history(self, message: Message) -> List[CacheMessage]:
        return self.messages_cache.get(message.chat.id)

    def normalize_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        res = []
        last = "model"
        for i in history:
            if i["role"] == last:
                res.append({"role": "model" if i["role"] == "user" else "user", "parts": [{"text": "."}]})
            last = i["role"]
            res.append(i)
        return res

    async def generate_chat_info(self, message: Message) -> str:
        if message.chat.type in ['group', 'supergroup']:
            chat_info = f"Информация о чате \nНазвание группы: {message.chat.title}"
            admins = await self.bot.get_chat_administrators(message.chat.id)
            admin_info = []
            for admin in admins:
                admin_info.append(f"{admin.user.full_name}: (@{admin.user.username or 'без username'})")

            chat_info += "; ".join(admin_info)
        else:
            chat_info = f"Информация о чате \nЧат с пользователем: @{message.chat.username}"
        return chat_info

    async def convert_history_to_dicts(self, history: List[CacheMessage], max_input_symbols: int,
                                       file_history: int) -> List[Dict[str, Any]]:
        messages = []
        count = 0

        for n, mes in enumerate(history):
            count += len(mes.text or "")
            if count > max_input_symbols:
                break
            messages.append(await self.convert_message_to_dict(mes, with_files=n <= file_history))

        messages = self.normalize_history(messages)
        return messages

    async def convert_message_to_dict(self, mes: CacheMessage, with_files: bool = False) -> Dict[str, Any]:
        cont = mes.text or ""
        if mes.autor == self.me.username:
            res = {"role": "model", "parts": [{"text": cont}]}
        else:
            res = {"role": "user", "parts": [{"text": f"@{mes.autor}: {cont}"}]}
        if with_files:
            if mes.files_uri:
                res["parts"].extend([{"file_data": {"file_uri": image}} for image in mes.files_uri])

        return res

    async def process_brain(self, message: Message, no_prompt=False) -> str:
        chat_info = await self.generate_chat_info(message)

        history = await self.load_history(message)
        messages = await self.convert_history_to_dicts(history, config.BotConfig.max_input_symbols,
                                                       config.BotConfig.file_history)

        chat_answer = await self.gpt.generate_answer(messages, additional_info=chat_info, no_prompt=no_prompt)
        if len(chat_answer) >= 4096:  # Max message len in Telegram
            chat_answer = chat_answer[:4091] + "..."
        return chat_answer

    async def clear(self, message: Message):
        self.messages_cache.clear_chat(message.chat.id)

    async def handle_message(self, message: Message):
        is_reply = message.reply_to_message and message.reply_to_message.from_user.username == self.me.username
        text = message.text or message.caption or ""
        if text.startswith("/clear"):
            await self.clear(message)
            return
        is_ping = f"@{config.BotConfig.name}" in text or self.me.username in text
        if is_reply or is_ping or message.chat.type == "private":
            async with BotAction(self.bot, message.chat.id, 'typing'):
                await self.add_to_history(message)

                if text.startswith("/gpt"):
                    answer = await self.process_brain(message, no_prompt=True)
                else:
                    answer = await self.process_brain(message, no_prompt=False)
                if answer:
                    converted = telegramify_markdown.markdownify(
                        answer,
                        max_line_length=None,
                        normalize_whitespace=False
                    )
                    await self.add_to_history(await message.reply(converted, parse_mode=ParseMode.MARKDOWN_V2))
        else:
            await self.add_to_history(message)

    async def start(self):
        await self.setup_me()
        logging.info("Starting...")
        await self.dp.start_polling(self.bot)


def run_bot():
    logging.basicConfig(level=logging.INFO)
    bot = TelegramBot()
    asyncio.run(bot.start())


if __name__ == '__main__':
    run_bot()
