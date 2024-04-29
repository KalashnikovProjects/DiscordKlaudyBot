import asyncio
import queue
import threading
import time

import config


class QueTimoutError(Exception):
    pass


def run_in_thread(coroutine):
    """
    Запускает асинхронную функцию в отдельном треде
    """
    threading.Thread(target=asyncio.run_coroutine_threadsafe, args=(coroutine, asyncio.get_event_loop())).start()


def background_que_process(rate_ques, rate_remained):
    while True:
        for i in range(len(rate_ques)):
            sleep_count = min(rate_ques[i].qsize(), rate_remained[i])
            for _ in range(sleep_count):
                event = rate_ques[i].get()
                event.set()
                rate_ques[i].task_done()
        time.sleep(0.1)

...


def rate_limit_timer_reset(rate_remained, index, max_rate_limit):
    time.sleep(60)
    if rate_remained[index] != max_rate_limit:
        rate_remained[index] += 1


def api_rate_limiter_with_ques(rate_per_minute, tokens, timeout=config.que_timeout):
    rate_ques = [queue.Queue() for _ in tokens]
    rate_remained = [rate_per_minute for _ in tokens]

    threading.Thread(target=background_que_process, daemon=True, args=(rate_ques, rate_remained)).start()

    def que_rate_limit_decorator(func):
        def wrapper(*args, **kwargs):
            que_index = max(enumerate(rate_remained), key=lambda x: x[1])[0]
            if not rate_ques[que_index].empty() or rate_remained[que_index] == 0:
                event = threading.Event()
                rate_ques[que_index].put(event)
                is_set = event.wait(timeout=timeout)
                if not is_set:
                    raise QueTimoutError("Таймаут очереди запросов")
            rate_remained[que_index] -= 1
            token = tokens[que_index]
            res = func(*args, token=token, **kwargs)
            threading.Thread(target=rate_limit_timer_reset, args=(rate_remained, que_index, rate_per_minute)).start()
            return res
        return wrapper

    return que_rate_limit_decorator
