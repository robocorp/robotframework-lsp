"""
Note: we have our own logging framework so that it doesn't conflict with the
regular logging framework usage (because when doing a robotframework launch it
disrupts the existing loggers).

Usage:

configure_logger('LSP', log_level, log_file)
log = get_logger(__name__)

...

log.debug('debug')
log.info('info')
log.critical('critical')
log.exception('error')

Note that we have 3 levels:
0: show only critical/exceptions
1: show info
2: show debug
"""
import os.path
import traceback
import threading
import sys
from datetime import datetime
from robocorp_ls_core.protocols import ILog
from typing import Dict
from robocorp_ls_core.constants import NULL

name_to_logger: Dict[str, ILog] = {}


def _as_str(s):
    if isinstance(s, bytes):
        return s.decode("utf-8", "replace")
    return s


MAX_LOG_MSG_SIZE = 2000
try:
    MAX_LOG_MSG_SIZE = int(os.environ.get("MAX_LOG_MSG_SIZE", MAX_LOG_MSG_SIZE))
except:
    pass


class _LogConfig(object):

    __slots__ = ["_lock", "__stream", "prefix", "log_level", "_log_file", "pid"]

    def __init__(self):
        self._lock = threading.Lock()
        self.__stream = None

        self.prefix = ""
        self.log_level = 0
        self.log_file = None
        self.pid = os.getpid()

    @property
    def log_file(self):
        return self._log_file

    @log_file.setter
    def log_file(self, log_file):
        with self._lock:
            if log_file is None:
                self._log_file = None
                self.__stream = None

            elif isinstance(log_file, str):
                self._log_file = log_file
                self.__stream = None

            else:
                assert hasattr(log_file, "write")
                self._log_file = None
                self.__stream = log_file

    @property
    def _stream(self):
        stream = self.__stream
        if stream is None:

            # open it on demand
            with self._lock:
                log_file = self._log_file
                if self.__stream is None:
                    stream = sys.stderr
                    if log_file:
                        stream = open(log_file, "w")
                    self.__stream = stream
                    return stream

        return stream

    def close_logging_streams(self):
        with self._lock:
            if self.__stream is not None:
                self.__stream.write("-- Closing logging streams --")
                self.__stream.close()
            self.__stream = NULL

    def report(self, logger_name, show_stacktrace, levelname, message, trim):
        if trim:
            msg_len = len(message)
            if msg_len > MAX_LOG_MSG_SIZE:
                message = f"{message[:MAX_LOG_MSG_SIZE-200]} ... <trimmed {msg_len} to {MAX_LOG_MSG_SIZE}> ... {message[-200:]}"

        log_format = (
            self.prefix
            + ": %(asctime)s UTC pid: %(process)d - %(threadname)s - %(levelname)s - %(name)s\n%(message)s\n\n"
        )
        msg = log_format % {
            "asctime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "process": self.pid,
            "threadname": threading.current_thread().name,
            "levelname": levelname,
            "name": logger_name,
            "message": message,
        }
        try:
            # Get stream without using the lock to avoid deadlocks.
            stream = self._stream
            with self._lock:
                stream.write(msg)
                if show_stacktrace:
                    traceback.print_exc(file=stream)
                stream.flush()
        except:
            pass  # Never fail when logging.


_log_config = _LogConfig()


def close_logging_streams():
    _log_config.close_logging_streams()


class _Logger(object):
    def __init__(self, name):
        self.name = name

    def critical(self, msg="", *args):
        if _log_config.log_level >= 0:
            self._report("CRITICAL", False, False, msg, *args)

    def exception(self, msg="", *args):
        if _log_config.log_level >= 0:
            self._report("EXCEPTION", True, False, msg, *args)

    def info(self, msg="", *args):
        if _log_config.log_level >= 1:
            self._report("INFO", False, True, msg, *args)

    def debug(self, msg="", *args):
        if _log_config.log_level >= 2:
            self._report("DEBUG", False, True, msg, *args)

    warn = warning = info
    error = exception

    @property
    def level(self):
        # Note: return a level compatible with the logging.
        import logging

        log_level = _log_config.log_level
        if log_level >= 2:
            return logging.DEBUG
        if log_level >= 1:
            return logging.INFO
        return logging.ERROR

    def _report(self, levelname, show_stacktrace, trim, msg="", *args):
        msg = _as_str(msg)
        if args:
            args = tuple(_as_str(arg) for arg in args)
            try:
                message = msg % args
            except:
                message = "%s - %s" % (msg, args)
        else:
            message = msg

        _log_config.report(self.name, show_stacktrace, levelname, message, trim)


def get_log_level():
    return _log_config.log_level


def get_log_file():
    return _log_config.log_file


def get_logger(name: str) -> ILog:
    """
    Use as:
        log = get_logger(__name__)
    """
    name = _as_str(name)
    try:
        return name_to_logger[name]
    except:
        name_to_logger[name] = _Logger(name)
    return name_to_logger[name]


def _configure_logger(prefix, log_level, log_file):
    _log_config.prefix = prefix
    _log_config.log_level = log_level
    _log_config.log_file = log_file


def _current_config():
    return _log_config.prefix, _log_config.log_level, _log_config.log_file


class _RestoreCtxManager(object):
    def __init__(self, config_to_restore):
        self._config_to_restore = config_to_restore

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        _configure_logger(*self._config_to_restore)


def configure_logger(postfix, log_level, log_file):
    """
    :param log_file:
        - If None, get target file from env var.
        - If empty string log to stderr.

    :note: If used as a context manager it'll revert to the previous
           configuration on `__exit__`.
    """

    prev_config = _current_config()

    if log_file:
        if isinstance(log_file, str):
            try:
                log_file = os.path.expanduser(log_file)
                log_file = os.path.realpath(os.path.abspath(log_file))
                dirname = os.path.dirname(log_file)
                basename = os.path.basename(log_file)
                try:
                    os.makedirs(dirname)
                except:
                    pass  # Ignore error if it already exists.

                name, ext = os.path.splitext(basename)
                log_file = os.path.join(
                    dirname, name + "." + postfix + "." + str(os.getpid()) + ext
                )
            except:
                log_file = None
                # Don't fail when trying to setup logging, just show the exception.
                traceback.print_exc()

    _configure_logger(postfix, log_level, log_file)
    return _RestoreCtxManager(prev_config)


def log_args_and_python(log, argv, module):
    log.info("Arguments: %s", argv)
    log.info(
        "Python: %s - lsp: %s (%s) - platform: %s - sys.prefix: %s - sys.executable: %s",
        sys.version,
        getattr(module, "__version__", "<unable to get __version__>"),
        module,
        sys.platform,
        sys.prefix,
        sys.executable,
    )
    log.info("CPUs: %s", os.cpu_count())
