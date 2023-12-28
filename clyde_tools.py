import config

voice_tools = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "leave_voice",
    #         "description": f"Используй что бы выйти из голосового канала (его также называют гс или войс), используй ТОЛЬКО если тебя просят выйти с указанием твоего имени, не используй если хочешь прекратить разговор, например: Выйди из войса, {config.name}",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "query": {},
    #             },
    #             "required": [],
    #         },
    #     }},
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": f"Используй что бы включить музыку по названию из Youtube, используй ТОЛЬКО если тебя просят это с указанием твоего имени например: Эй, {config.name}, включи OFMG - HELLO",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Запрос, который пользователь просит найти (будет искать на Youtube)",
                    }
                },
                "required": ["query"],
            },
        }},
    {
        "type": "function",
        "function": {
            "name": "off_music",
            "description": f"Используй что бы выключить музыку, которая сейчас играет, используй ТОЛЬКО если тебя просят это с указанием твоего имени например: Эй, {config.name}, выруби музыку.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }}
]

text_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_gif_on_tenor",
            "description": "находит ссылку на gif (гифку) по любой теме с помощью Tenor. Вставь эту ссылку в своё сообщение что бы в чате увидели гифку.",
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
    {
        "type": "function",
        "function": {
            "name": "enjoy_voice",
            "description": "Присоединяет бота (тебя) к голосовому каналу дискорд (их также называют гс или войс), в котором находится отправитель сообщения. Убедись что тебя просят зайти в голосовой канал, перед тем как это использовать.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
            "required": [],
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_from_text",
            "description": "Включает музыку в голосовом канале.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Запрос, который пользователь просит найти (будет искать на Youtube), используй ТОЛЬКО если тебя просят это с указанием твоего имени например: Эй, {config.name}, выруби музыку.",
                    }},
            },
            "required": ["query"],
        },
    },
{
        "type": "function",
        "function": {
            "name": "stop_from_text",
            "description": f"Используй что бы выключить музыку, которая сейчас играет в голосовом канале, используй ТОЛЬКО если тебя просят это с указанием твоего имени например: Эй, {config.name}, выруби музыку.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }}
    # временно отключено, бот слишком часто использовал
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
