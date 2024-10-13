import asyncio
import queue
import threading
import time

from . import config


class QueTimoutError(Exception):
    pass


def run_in_thread(coroutine):
    """
    Run async function in thread
    """
    threading.Thread(target=asyncio.run_coroutine_threadsafe, args=(coroutine, asyncio.get_event_loop())).start()


def background_rate_limit_que_process(rate_ques, last_request_time, rate_limit_time):
    while True:
        for i in range(len(rate_ques)):
            count_free = 0
            for j in last_request_time[i]:
                if j + rate_limit_time <= time.time():
                    count_free += 1
            sleep_count = min(rate_ques[i].qsize(), count_free)
            for _ in range(sleep_count):
                event = rate_ques[i].get()
                event.set()
                rate_ques[i].task_done()
        time.sleep(0.1)


def api_rate_limiter_with_ques(rate_limit, tokens, timeout=config.QUE_TO_GENERATE_TIMEOUT, rate_limit_time=60):
    """
    The decorator sets a queue limit for the rate function, with support for multiple tokens (multiple queues)
, The decorated function must necessarily accept the token argument, it is passed to it from the decorator

    Decorator Arguments:
    tokens - a list of tokens (for cases when there are several accounts with separate limits, otherwise 1 element),
    timeout - timeout for finding an item in the queue
    rate_limit - limit of function calls,
    rate_limit_time=60 - the limit for what time

    Tasks for which there was not enough limit are postponed to the queue, queue items -
    threading.Event(), events are served in a separate thread, the wrapper function waits for the event and starts.
    """
    rate_ques = [queue.Queue() for _ in tokens]
    last_request_time = [[time.time() - rate_limit_time for _ in range(rate_limit)] for _ in tokens]

    threading.Thread(target=background_rate_limit_que_process, daemon=True, args=(rate_ques, last_request_time, rate_limit_time)).start()

    def que_rate_limit_decorator(func):
        def wrapper(*args, **kwargs):
            que_index = min(enumerate(last_request_time), key=lambda x: min(x[1]))[0]
            last_req_time_index, last_req_time = min(enumerate(last_request_time[que_index]), key=lambda x: x[1])

            if not rate_ques[que_index].empty() or last_req_time + rate_limit_time > time.time():
                event = threading.Event()
                rate_ques[que_index].put(event)
                is_set = event.wait(timeout=timeout)
                if not is_set:
                    raise QueTimoutError("Que rate limiter timeout")
            last_request_time[que_index][last_req_time_index] = time.time()
            token = tokens[que_index]
            res = func(*args, token=token, **kwargs)
            return res
        return wrapper

    return que_rate_limit_decorator
