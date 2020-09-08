import threading


class _ThreadPoolHolder(object):

    _lock = threading.Lock()
    _thread_pool = None


def obtain_thread_pool():
    with _ThreadPoolHolder._lock:
        thread_pool = _ThreadPoolHolder._thread_pool
        if thread_pool is not None:
            return thread_pool

        from concurrent import futures
        import os

        max_workers = min(32, (os.cpu_count() or 1) + 4)
        _ThreadPoolHolder._thread_pool = futures.ThreadPoolExecutor(
            max_workers=max_workers
        )

    return _ThreadPoolHolder._thread_pool


def dispose_thread_pool() -> None:
    with _ThreadPoolHolder._lock:
        thread_pool = _ThreadPoolHolder._thread_pool
        if thread_pool is None:
            return
        _ThreadPoolHolder._thread_pool = None
        thread_pool.shutdown()
