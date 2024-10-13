import logging
import aiohttp
import html2text
from bs4 import BeautifulSoup

from . import config


async def fake_func(*args, **kwargs):
    return "Ты пытаешься вызвать несуществующую функцию"


text_tools = {'function_declarations': [
    {
        "name": "search_gif_on_tenor",
        "description": "найти ссылку на gif (гифку) по любой теме с помощью Tenor.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Запрос для поиска",
                }},
            "required": ["query"],
        },
    },
    {
        "name": "link_checker",
        "description": "Просматривает содержимое сайта, если на нём много текста напишет его краткий пересказ",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Ссылка на сайт или статью.",
                }},
            "required": ["url"],
        },
    },
]}


class TextTools:
    def __init__(self, gpt_obj):
        self.gpt_obj = gpt_obj
        self.html2text_client = html2text.HTML2Text()
        self.html2text_client.ignore_links = True
        self.html2text_client.ignore_images = True
        self.html2text_client.unicode_snob = True
        self.html2text_client.decode_errors = 'replace'

    async def simple_link_checker(self, url):
        """
        Версия проверки ссылок без использования нейросети от Яндекса (просто текст страницы)
        В данный момент не используется
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, timeout=config.REQUESTS_TIMEOUT) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                    if len(text) > 2000:
                        text = text[:2000]
                    return text
        except Exception as e:
            logging.warning(f"simple_link_checker - {e}")
            return f"Ошибка {e}"

    async def link_checker(self, url):
        """
        Проверяет текстовое содержание ссылки.
        Если текста не много, использует его
        Если много, то использует нейросеть от Яндекса 300.ya.ru для выделения главного
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                async with await aiohttp_session.get(url, timeout=config.REQUESTS_TIMEOUT) as res:
                    res.encoding = 'UTF-8'
                    text = self.html2text_client.handle(await res.text())
                if len(text) < 4000:
                    if len(text) > 1200:
                        text = text[:1200] + "..."
                    return text
                auth = f'OAuth {config.Ya300.token}'
                async with await aiohttp_session.post(config.Ya300.server, json={"article_url": url},
                                                      headers={"Authorization": auth},
                                                      timeout=config.REQUESTS_TIMEOUT) as response:
                    data = await response.json()

                if data["status"] != "success":
                    text = text[:1200] + "..."
                    return text
                async with aiohttp_session.get(data["sharing_url"], timeout=config.REQUESTS_TIMEOUT) as res:
                    res.encoding = 'UTF-8'
                    soup = BeautifulSoup(await res.text(), 'html.parser')

                    # Находим все элементы, соответствующие селектору '.thesis-text span'
                    res = f"{soup.select('h1.title')[0].text}\n"
                    thesis_elements = soup.select('.thesis-text span')
                    for i in thesis_elements:
                        if len(i.text) > 2:
                            res += f"{i.text}\n"

                    if len(res) > 1200:
                        res = res[:1200] + '...'
                    return res
        except Exception as e:
            logging.warning(f"link_checker - {e}")
            return f"Ошибка {e}"

    @staticmethod
    async def search_gif_on_tenor(query):
        try:
            api_key = config.Tenor.token
            url = config.Tenor.server

            params = {
                'q': query,
                'key': api_key,
                'limit': 1,
                'ckey': "my_test_app"
            }
            async with aiohttp.ClientSession() as aiohttp_session:
                async with aiohttp_session.get(url, params=params, timeout=config.REQUESTS_TIMEOUT) as response:
                    data = await response.json()
                    if len(data['results']) == 0:
                        return "`Не нашлось гифок`"
                    gif_url = data['results'][0]['media_formats']["gif"]["url"]
                    return gif_url
        except Exception as e:
            logging.warning(f"search_gif_on_tenor - {e}")
            return f"Ошибка {e}"
