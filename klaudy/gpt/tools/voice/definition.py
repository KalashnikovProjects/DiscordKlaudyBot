VOICE_TOOLS_DEFINITION = [
    {
        "name": "play_music",
        "behavior": "NON_BLOCKING",
        "description": "включить музыку, например: OFMG - HELLO, если тебя просят включить Чипи чипи чапа чапа (или похожее или на английском) - не делай этого",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Запрос для поиска на Youtube",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "off_music",
        "behavior": "NON_BLOCKING",
        "description": "выключить музыку и включить следующий трек из очереди",
        "parameters": {
            "type": "object",
            "properties": {
                "mixer": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    {
        "name": "get_que",
        "description": "получить очередь музыки и трек, который сейчас играет.",
        "parameters": {
            "type": "object",
            "properties": {
                "mixer": {
                    "type": "string",
                    "description": "Комментарий",
                }},
            "required": [],
        },
    },
    # временно отключено, бот слишком часто использовал
    # {
    #     "name": "leave_voice",
    #     "description": "Используй что бы выйти из голосового канала",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {},
    #         "required": [],
    #     },
    # },
]