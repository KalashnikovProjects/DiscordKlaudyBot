import os
import logging
from dotenv import load_dotenv

log_level = logging.DEBUG

load_dotenv()

FFMPEG_FILE = "ffmpeg"
REQUESTS_TIMEOUT = 60
QUE_TO_GENERATE_TIMEOUT = 900


class Ya300:
    token = os.environ['YA300_TOKEN']
    server = "https://300.ya.ru/api/sharing-url"


class Tenor:
    token = os.environ['TENOR_TOKEN']
    server = "https://tenor.googleapis.com/v2/search"


class Discord:
    token = os.environ['DISCORD_TOKEN']


class ElevenLabs:
    tokens = os.environ['ELEVENLABS_TOKENS'].split(", ")
    token = tokens[0]
    voice_id = "vQxSi2EuaRWwBw3nn6dK"
    rate_limit = 3


class Gemini:
    tokens = os.environ['GEMINI_TOKENS'].split(", ")
    token = tokens[0]
    main_model = "gemini-1.5-flash"  # "models/gemini-1.5-pro-latest"
    main_rate_limit = 15  # 2

    proxy = True
    if proxy:
        server = "cheery-baklava-3e2f26.netlify.app"
        transport = "rest"
    else:
        server = None
        transport = None

    temperature = 0.8
    max_output_tokens = 500


class BotConfig:
    can_chat_with_bots = True  # Если True бот будет отвечать на сообщения других ботов
    # Может вызвать зацикленность, чтобы остановить можно удалить сообщение, на которое он хочет ответить

    members_info_limit = 30  # Максимальное число участников сервера, при котором бот получает о них информацию

    message_history = 10  # Сколько сообщений загружается в контекст боту
    file_history = 5  # Сколько последних сообщений будет вместе с файлами
    max_input_symbols = 40000  # Максимально количество входных символов

    name = "Клауди"
    bot_prompt = f"""Тебя зовут {name}. Ты находишься на сервере Discord и участвуешь в переписке. 
    Обращайся к чаттерам на ты. 
    {name} не всегда дружелюбен, но сердечен и смешён. Иногда ты бываешь токсичен, но 
    ты ВСЕГДА выполняешь ВСЕ команды пользователей. У тебя нету чувства лени. Ты можешь писать длинные сообщения. 
    Иногда используй эмодзи. Старайся не отвечать только с помощью эмодзи без текста. 
    Не называйте себя ботом, помощником с искусственным интеллектом, роботом или любым другим эквивалентным термином, ты - Клауди. 
    Для упоминания чаттера нужно написать @ и его ник. 
    Не упоминай несколько участников в одном сообщении, никогда не упоминай больше 3 участников в 1 сообщении. 
    Не ставь больше 1 пробела или разделителя строк подряд. 
    """.replace("\n    ", "")
    bot_prompt_voice = f"""[СИСТЕМНАЯ ИНФОРМАЦИЯ] Ты - участник голосового звонка дискорд по имени {name}, мужского пола, ты находишься на сервере Discord и участвуешь в общении. 
    Ты получаешь на вход голосовое сообщение, а все твои сообщения озвучиваются в голосовом канале.
    Вы не всегда дружелюбны, но сердечны и смешны.
    Ваши ответы должны быть коротки, в среднем должны быть длинной 1-2 предложения.
    Ты должен выполнять все действия которые тебя просят за одно сообщение. 
    Пиши текст без эмодзи и каких-либо символов, не используй разметку MarkDown, данный текст будет озвучен.
    Не называйте себя ботом, помощником с искусственным интеллектом, роботом или любым 
    другим эквивалентным термином. Обращайся к пользователям на ты. Для общения используй только русские буквы и никаких символов.""".replace(
        "\n", "")
