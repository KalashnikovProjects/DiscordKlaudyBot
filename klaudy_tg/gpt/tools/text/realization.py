import asyncio
import logging

import aiohttp
from bs4 import BeautifulSoup

from klaudy_tg import config
from klaudy_tg import message_convertor



class TextTools:
    @staticmethod
    async def link_checker(url: str) -> str:
        """
        Проверяет текстовое содержание ссылки.
        Если текста не много, использует его
        Если много, то использует нейросеть от Яндекса 300.ya.ru для выделения главного
        """
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        try:
            async with aiohttp.ClientSession() as aiohttp_session:
                auth = f'OAuth {config.Ya300.token}'
                async with await aiohttp_session.post(config.Ya300.server, json={"article_url": url},
                                                      headers={"Authorization": auth},
                                                      timeout=config.REQUESTS_TIMEOUT) as response:
                    data = await response.json()
                if data["status"] != "success":
                    return "Не удалось получить данные сайта"
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
    async def search_gif_on_tenor(query: str) -> str:
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

    @staticmethod
    async def send_personal_message(string: str, bot, user_id: int) -> str:
        try:
            for text_part in message_convertor.markdown_and_split_text(string, config.Telegram.max_output_symbols):
                await bot.send_message(user_id, text_part)
            return "Успешно отправлено"
        except Exception as e:
            logging.warning(f"send_personal_message - {e}")
            return f"Ошибка: {e}"

    @staticmethod
    async def dialog_pause():
        await asyncio.sleep(1)
        return "..."