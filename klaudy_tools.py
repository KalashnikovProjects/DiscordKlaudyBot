
voice_tools = {'function_declarations': [
    # временно отключено, бот слишком часто использовал
    # {
    #     "name": "leave_voice",
    #     "description": "Используй что бы выйти из голосового канала",
    #     "parameters": {
    #         "type_": "OBJECT",
    #         "properties": {},
    #         "required": [],
    #     },
    # },
    {
        "name": "play_music",
        "description": "Только эта функция может включить музыку, например: OFMG - HELLO",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "query": {
                    "type_": "STRING",
                    "description": "Запрос для поиска на Youtube",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "off_music",
        "description": "Только эта функция может выключить музыку и включить следующий трек",
        "parameters": {
            "type_": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_que",
        "description": "Только эта функция может получить реальную очередь музыки и трек, который сейчас играет.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
]}

text_tools = {'function_declarations': [
    {
        "name": "search_gif_on_tenor",
        "description": "находит ссылку на gif (гифку) по любой теме с помощью Tenor.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "query": {
                    "type_": "STRING",
                    "description": "Запрос для поиска",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "link_checker",
        "description": "Просматривает содержимое сайта, если на нём много текста напишет его краткий пересказ",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "url": {
                    "type_": "STRING",
                    "description": "Ссылка на сайт или статью.",
                }},
            "required": ["url"],
        },
    },
    {
        "name": "enjoy_voice",
        "description": "Только эта функция позволяет присоединиться в голосовой канал к собеседнику",
        "parameters": {
            "type_": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "play_from_text",
        "description": "Только эта функция может включить музыку в голосовом канале, например: OFMG - HELLO",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "query": {
                    "type_": "STRING",
                    "description": "Запрос для поиска на Youtube",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "stop_from_text",
        "description": "Только эта функция может выключить музыку и включить следующий трек",
        "parameters": {
            "type_": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_que_from_text",
        "description": "Только эта функция может получить реальную очередь музыки и трек, который сейчас играет.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {},
            "required": [],
        },
    },
    # временно отключено, бот слишком часто использовал
    # {
    #     "name": "get_member",
    #     "description": "Получает доступную информацию о пользователе по его никнейму.",
    #     "parameters": {
    #         "type_": "OBJECT",
    #         "properties": {
    #             "nick": {
    #                 "type_": "STRING",
    #                 "description": "Ник пользователя",
    #             }},
    #         "required": ["nick"],
    #     },
    # },
]}
