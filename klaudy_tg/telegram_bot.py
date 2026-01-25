import enum
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import AsyncGenerator
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
import telegramify_markdown

from klaudy_tg.gpt import TextGPT
from . import config, message_convertor, utils

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


# download with https://api.telegram.org/file/bot<token>/<file_path> or await bot.download_file(file_path, <BinaryIO>)
@dataclass
class MessageFile:
    file_path: str


@dataclass
class CachedMessage:
    autor: str
    text: str
    files: list[MessageFile] = field(default_factory=list)


@dataclass
class ChatData:
    message_list: list[CachedMessage] = field(default_factory=list)
    gpt_mode_toggled: bool = False


class SpecialCommand(enum.Enum):
    START=1
    HELP=2
    CLEAR=3
    GPT=4

class TelegramBot:
    def __init__(self):
        self.storage: dict[int, ChatData] = defaultdict(ChatData)

        self.bot_user = None
        self.bot = Bot(token=config.Telegram.token)
        self.dp = Dispatcher()
        self.text_gpt = TextGPT()
        self.setup_handlers()

    async def setup_bot_user(self):
        self.bot_user = await self.bot.get_me()

    async def add_to_history(self, message: Message):
        files = await self.get_message_files(message)
        text = message.text or message.caption or ""

        mes = CachedMessage(autor=message.from_user.username, text=text, files=files)
        self.storage[message.chat.id].message_list.append(mes)
        if len(self.storage[message.chat.id].message_list) > config.BotConfig.message_history:
            self.storage[message.chat.id].message_list.pop(0)


    async def get_message_files(self, message: Message) -> list[MessageFile]:
        res = []
        if message.photo:
            for photo in message.photo:
                file = await self.bot.get_file(photo.file_id)
                res.append(MessageFile(file.file_path))
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

    def normalize_history(self, history):
        res = []
        last = "assistant"
        for i in history:
            if i["role"] == last:
                res.append({"role": "assistant" if i["role"] == "user" else "user", "parts": [{"text": "."}]})
            res.append(i)
            last = i["role"]
        return res

    async def convert_history_to_dicts(self, history, max_input_symbols: int,
                                       file_history: int):
        messages = []
        count = 0

        for n, mes in enumerate(history):
            count += len(mes.text or "")
            if count > max_input_symbols:
                break
            messages.append(await self.convert_message_to_dict(mes, with_files=n <= file_history))

        messages = self.normalize_history(messages)
        return messages

    async def convert_message_to_dict(self, mes: CachedMessage, with_files: bool = False):
        cont = mes.text or ""
        if mes.autor == self.bot_user.username:
            res = {"role": "assistant", "content": [{"type": "text", "text": cont}]}
        else:
            res = {"role": "user", "content": [{"type": "text", "text": f"@{mes.autor}: {cont}"}]}
        if with_files and mes.files:
            for file in mes.files:
                res["content"].append({"type": "image_url", "image_url": f"https://api.telegram.org/file/bot{config.Telegram.token}/{file.file_path}"})
        return res


    async def process_brain_parts(self, message: Message, special_command: SpecialCommand | None = None) -> AsyncGenerator:
        chat_info = await self.generate_chat_info(message)

        chat_data = self.storage[message.chat.id]
        messages = await self.convert_history_to_dicts(chat_data.message_list, config.BotConfig.max_input_symbols,
                                                       config.BotConfig.file_history)

        bot_prompt = config.BotConfig.bot_prompt if not chat_data.gpt_mode_toggled else config.BotConfig.gpt_mode
        if special_command:
            match special_command:
                case SpecialCommand.START:
                    bot_prompt = config.BotConfig.start_prompt if not chat_data.gpt_mode_toggled else config.BotConfig.start_prompt_gpt_mode
                case SpecialCommand.HELP:
                    bot_prompt = config.BotConfig.help_prompt if not chat_data.gpt_mode_toggled else config.BotConfig.help_prompt_gpt_mode
                case SpecialCommand.CLEAR:
                    bot_prompt = config.BotConfig.clear_prompt if not chat_data.gpt_mode_toggled else config.BotConfig.clear_prompt_gpt_mode
                case SpecialCommand.GPT:
                    bot_prompt = config.BotConfig.gpt_prompt if not chat_data.gpt_mode_toggled else config.BotConfig.gpt_prompt_prompt_gpt_mode
        async for part in self.text_gpt.generate_answer_parts(messages_history=messages,
                                                              bot=self.bot,
                                                              sender_user_id=message.from_user.id,
                                                              bot_prompt=bot_prompt,
                                                              additional_info=chat_info,
                                                              is_pm=message.chat.type in ['group', 'supergroup']):
            for text_part in message_convertor.markdown_and_split_text(part, config.Telegram.max_output_symbols):
                yield text_part

    async def clear(self, message: Message):
        self.storage[message.chat.id].message_list.clear()

    async def toggle_gpt(self, message: Message):
        self.storage[message.chat.id].gpt_mode_toggled = not self.storage[message.chat.id].gpt_mode_toggled

    async def handle_message(self, message: Message):
        is_reply = message.reply_to_message and message.reply_to_message.from_user.username == self.bot_user.username
        text = message.text or message.caption or ""
        special_command = None
        match text.split()[0]:
            case "/clear":
                special_command = SpecialCommand.CLEAR
                await self.clear(message)
            case "/gpt":
                special_command = SpecialCommand.GPT
                await self.clear(message)
                await self.toggle_gpt(message)
            case "/start":
                special_command = SpecialCommand.START
            case "/help":
                special_command = SpecialCommand.HELP
            case _:
                is_ping = f"@{config.BotConfig.name}" in text or self.bot_user.username in text
                if not (is_reply or is_ping or message.chat.type == "private"):
                    await self.add_to_history(message)
        async with BotAction(self.bot, message.chat.id, 'typing'):
            await self.add_to_history(message)
            is_first_reply_flag = True
            async for part in self.process_brain_parts(message, special_command):
                if part == "":
                    continue
                if is_first_reply_flag:
                    mes = await message.reply(part, parse_mode=ParseMode.MARKDOWN_V2)
                else:
                    mes = await self.bot.send_message(message.chat.id, part, parse_mode=ParseMode.MARKDOWN_V2)
                await self.add_to_history(mes)



    async def start(self):
        await self.setup_bot_user()
        logging.info("Starting...")
        await self.dp.start_polling(self.bot)

    def setup_handlers(self):
        self.dp.message.register(self.handle_message)


def run_bot():
    logging.basicConfig(level=logging.INFO)
    bot = TelegramBot()
    asyncio.run(bot.start())


if __name__ == '__main__':
    run_bot()
