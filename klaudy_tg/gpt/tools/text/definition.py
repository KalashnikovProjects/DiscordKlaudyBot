TOOLS_NAMES_ENABLED_FOR_PM = ["search_gif_on_tenor", "link_checker", "dialog_pause"]

TEXT_TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "search_gif_on_tenor",
            "description": "найти ссылку на gif (гифку) по любой теме с помощью Tenor. потом эту ссылку тебе нужно будет вставить в сообщение.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Запрос для поиска",
                    }},
                "required": ["query"],
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "link_checker",
            "description": "Просматривает содержимое сайта, пишет его краткий пересказ",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Ссылка на сайт или статью.",
                    }},
                "required": ["url"],
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_personal_message",
            "description": "отправить личное сообщение чаттер. Ты можешь это использовать для запугивания или просто слома 4 стены (в редких случаях, когда чаттер этого максимально не ожидает). Ты пишешь сообщение в лс ТОМУ ЖЕ человеку, что и просто отвечаешь.",
            "parameters": {
                "type": "object",
                "properties": {
                    "string": {
                        "type": "string",
                        "description": "Сообщение",
                    }},
                "required": ["string"],
            },
            "strict": True
        }
    },
    {
        "type": "function",
        "function": {
            "name": "dialog_pause",
            "description": "пауза между частями сообщения. Используй зачастую чтобы отправлять свой ответ в несколько кусков, как будто ты реальный человек.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "strict": True
        }
    }
]

TEXT_TOOLS_ENABLED_FOR_PM_DEFINITION = [i for i in TEXT_TOOLS_DEFINITION if i["function"]["name"] in TOOLS_NAMES_ENABLED_FOR_PM]