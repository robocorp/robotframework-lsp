from robocorp_ls_core.basic import implements
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import IDirCache, check_implements, T
from robocorp_ls_core.robotframework_log import get_logger

from collections import namedtuple
from pathlib import Path
from typing import Any, Generic, Callable, Optional
import functools
import os


log = get_logger(__name__)


def instance_cache(func):
    """
    Use as decorator:
    
    class MyClass(object):

        @instance_cache
        def cache_this(self):
            ...
            
    Clear the cache with:
    
    instance = MyClass()
    instance.cache_this()
    instance.cache_this.cache_clear(instance)
    
    # set_lock(instance, lock) can be used to make the cache thread-safe.
    # i.e.:
    instance.cache_this.set_lock(instance, lock) 

    """
    cache_key = "__cache__%s" % (func.__name__,)
    cache_key_lock = "__cache__%s_lock" % (func.__name__,)

    @functools.wraps(func)
    def new_func(self, *args, **kwargs):
        from robocorp_ls_core.protocols import Sentinel

        try:
            cache = getattr(self, "__instance_cache__")
        except:
            cache = {}
            setattr(self, "__instance_cache__", cache)

        lock = cache.get(cache_key_lock, NULL)
        with lock:
            try:
                func_cache = cache[cache_key]
            except KeyError:
                func_cache = cache[cache_key] = {}

            args_cache_key = None
            if args:
                args_cache_key = (args_cache_key, tuple(args))
            if kwargs:
                # We don't do that because if the caller uses args and then
                # later kwargs, we'd have to match the parameter to the position,
                # so, simplify for now and don't accept kwargs.
                raise AssertionError("Cannot currently deal with kwargs.")

            ret = func_cache.get(args_cache_key, Sentinel)
            if ret is Sentinel:
                ret = func(self, *args, **kwargs)
                func_cache[args_cache_key] = ret
            return ret

    def set_lock(self, lock):
        # Note that this will make sure we'll pre-create the lock so that
        # the __instance_cache__ is always there (so, there should be
        # no race condition for it).
        try:
            cache = getattr(self, "__instance_cache__")
        except:
            cache = {}
            setattr(self, "__instance_cache__", cache)

        cache[cache_key_lock] = lock

    def cache_clear(self):
        try:
            cache = getattr(self, "__instance_cache__")
        except:
            pass
        else:
            lock = cache.get(cache_key_lock, NULL)
            with lock:
                cache.pop(cache_key, None)

    new_func.cache_clear = cache_clear
    new_func.set_lock = set_lock
    return new_func


class DirCache(object):
    """
    To be used as:
    
    dir_cache = DirCache(cache_directory)
    dir_cache.store("some_key", 1)
    value = dir_cache.load("some_key", int) # Ok
    
    try:
        value = dir_cache.load("some_key", dict)
    except KeyError:
        ... error: value is not a dict
    
    try:
        dir_cache.load("key does not exist", dict)
    except KeyError:
        ... error, key does not exist
    """

    def __init__(self, cache_directory: str) -> None:
        self._cache_dir = cache_directory
        os.makedirs(self._cache_dir, exist_ok=True)

    def _encode_key(self, key: Any) -> str:
        import hashlib

        return hashlib.sha224(repr(key).encode("utf-8")).hexdigest()

    def _get_file_for_key(self, key: Any) -> str:
        key_encoded = self._encode_key(key)
        return os.path.join(self._cache_dir, key_encoded)

    @implements(IDirCache.store)
    def store(self, key, value):
        import json

        with open(self._get_file_for_key(key), "w") as stream:
            stream.write(json.dumps({"key": key, "value": value}))

    @implements(IDirCache.load)
    def load(self, key, expected_class):
        import json

        filename = self._get_file_for_key(key)
        if not os.path.exists(filename):
            raise KeyError(f"Key: {key} not found in cache.")

        try:
            with open(filename, "r") as stream:
                contents = json.loads(stream.read())
            value = contents["value"]

        except Exception:
            msg = f"Unable to load key: {key} from cache."
            log.debug(msg)
            raise KeyError(msg)

        if not isinstance(value, expected_class):
            raise KeyError(
                f"Unable to load key: {key} from cache (expected it to be a {expected_class} was {type(value)}."
            )
        return value

    @implements(IDirCache.discard)
    def discard(self, key):
        filename = self._get_file_for_key(key)
        try:
            os.remove(filename)
        except Exception:
            pass

    def __typecheckself__(self) -> None:
        _: IDirCache = check_implements(self)


CachedFileMTimeInfo = namedtuple("CachedFileMTimeInfo", "st_mtime, st_size, path")


class CachedFileInfo(Generic[T]):
    def __init__(self, file_path: Path, compute_value: Callable[[Path], T]):
        self._file_path = file_path
        self._mtime_info: Optional[CachedFileMTimeInfo] = self._get_mtime_cache_info(
            file_path
        )
        # Note that we only get the value after getting the mtime (so, the
        # constructor receives a callable and not the value so that the cache
        # has no risk of having stale values).
        self._value = compute_value(file_path)

    @property
    def value(self) -> T:
        return self._value

    @property
    def file_path(self) -> Path:
        return self._file_path

    def _get_mtime_cache_info(self, file_path: Path) -> Optional[CachedFileMTimeInfo]:
        """
        Cache based on the time/size of a given path.
        """
        try:
            stat = file_path.stat()
            return CachedFileMTimeInfo(stat.st_mtime, stat.st_size, str(file_path))
        except:
            # Probably removed in the meanwhile.
            log.exception(f"Unable to get mtime for: {file_path}")
            return None

    def is_cache_valid(self) -> bool:
        return self._mtime_info == self._get_mtime_cache_info(self.file_path)
