import asyncio
import threading


def run_in_thread(coroutine):
    """
    Запускает асинхронную функцию в отдельном треде
    """
    threading.Thread(target=asyncio.run_coroutine_threadsafe, args=(coroutine, asyncio.get_event_loop())).start()