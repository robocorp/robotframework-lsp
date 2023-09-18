"""
Adapted to work without robocorp-tasks.
"""

import functools
import inspect
import threading

from robocorp_ls_core.callbacks import Callback


def _cache(callback, func):
    """
    Helper function to create cache decorator for the result of calling
    some function and clearing the cache when the given callback is called.
    """
    tlocal = threading.local()

    def _get_tlocal_cache():
        try:
            return tlocal.cache
        except AttributeError:
            tlocal.cache = []
            return tlocal.cache

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        if _get_tlocal_cache():
            return _get_tlocal_cache()[0]

        if inspect.isgeneratorfunction(func):
            iter_in = func(*args, **kwargs)
            _get_tlocal_cache().append(next(iter_in))

            def on_finish(*args, **kwargs):
                try:
                    next(iter_in)
                except StopIteration:
                    pass  # Expected
                finally:
                    _get_tlocal_cache().clear()
                    callback.unregister(on_finish)

            callback.register(on_finish)
        else:
            _get_tlocal_cache().append(func(*args, **kwargs))

            def on_finish(*args, **kwargs):
                _get_tlocal_cache().clear()
                callback.unregister(on_finish)

            callback.register(on_finish)

        return _get_tlocal_cache()[0]

    # The cache can be manually cleaned if needed.
    # (for instance, if the given object becomes invalid
    # the cache should be cleaned -- i.e.: if a browser
    # page is closed the cache can be cleaned so that
    # a new one is created).
    def clear_cache():
        cache = getattr(tlocal, "cache", None)
        if cache is not None:
            cache.clear()

    new_func.clear_cache = clear_cache

    return new_func


clear_all_callback = Callback()


def session_cache(func):
    return _cache(clear_all_callback, func)


def task_cache(func):
    return _cache(clear_all_callback, func)
