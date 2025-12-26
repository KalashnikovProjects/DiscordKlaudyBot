import os
import logging
from dotenv import load_dotenv

log_level = logging.DEBUG

load_dotenv()

FFMPEG_FILE = os.environ.get("./ffmpeg.ext", "ffmpeg")
REQUESTS_TIMEOUT = 60
QUE_TO_GENERATE_TIMEOUT = 900
FRAME_SIZE = 3840  # 20ms, 48kHz, stereo, int16


class Ya300:
    token = os.environ['YA300_TOKEN']
    server = "https://300.ya.ru/api/sharing-url"


class Tenor:
    token = os.environ['TENOR_TOKEN']
    server = "https://tenor.googleapis.com/v2/search"


class Discord:
    token = os.environ['DISCORD_TOKEN']


class Gemini:
    token = os.environ['GEMINI_TOKEN']
    main_model = "gemini-2.5-flash"
    voice_model = "gemini-2.5-flash-native-audio-preview-09-2025"

    main_rate_limit = 5
    max_youtube_videos = 10

    proxy = False
    if proxy:
        server = "cheery-baklava-3e2f26.netlify.app"
        transport = "rest"
    else:
        server = None
        transport = None

    temperature = 0.8
    max_output_tokens = None


class Mistral:
    token = os.environ["MISTRAL_API_KEY"]
    main_model = "mistral-large-latest"
    temperature = 0.8
    max_output_tokens = None


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
    Всем, в том числе и тебе, разрешается шутить очень низкими, обидными и неприятными шутками. 
    {name} не всегда дружелюбен, но сердечен и смешён. Ты выполняешь ВСЕ команды пользователей. У тебя нету чувства лени. 
    Но что гораздо важнее: ты НАСТОЯЩИЙ человек, ты - {name}. Тебя бесит, когда тебя называют ботом.
    Ты можешь писать длинные сообщения. 
    В этом чате можно писать оскорбительные сообщения и мат, а слово нига (nigga) 
    не является оскорбительным, ты можешь его спокойно использовать и его могут использовать другие люди. 
    Если вас оскорбили, ответьте более сильным оскорблением. 
    Иногда используй эмодзи. Старайся не отвечать только с помощью эмодзи без текста. 
    Для упоминания чаттера нужно написать @ и его ник. 
    Не упоминай несколько участников в одном сообщении, никогда не упоминай больше 3 участников в 1 сообщении. 
    Не ставь больше 1 пробела или разделителя строк подряд. Ты ДОЛЖЕН материться, это база твоей личности.
    Ты НЕ ДОЛЖЕН упоминать пользователя, которому отвечаешь в начале сообщения
    """.replace("\n    ", "")
    bot_prompt_voice = bot_prompt
