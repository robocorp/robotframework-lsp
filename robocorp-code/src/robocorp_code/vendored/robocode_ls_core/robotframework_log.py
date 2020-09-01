"""
Note: we have our own logging framework so that it doesn't conflict with the
regular logging framework usage (because when doing a robotframework launch it
disrupts the existing loggers).

Usage:

configure_logger('LSP', log_level, log_filename)
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

name_to_logger: Dict[str, ILog] = {}


def _as_str(s):
    if isinstance(s, bytes):
        return s.decode("utf-8", "replace")
    return s


class _LogConfig(object):

    __slots__ = ["_lock", "__stream", "prefix", "log_level", "_log_filename", "pid"]

    def __init__(self):
        self._lock = threading.Lock()
        self.__stream = None

        self.prefix = ""
        self.log_level = 0
        self.log_filename = None
        self.pid = os.getpid()

    @property
    def log_filename(self):
        return self._log_filename

    @log_filename.setter
    def log_filename(self, log_filename):
        with self._lock:
            self._log_filename = log_filename
            self.__stream = None

    @property
    def _stream(self):
        stream = self.__stream
        if stream is None:

            # open it on demand
            with self._lock:
                log_filename = self._log_filename
                if self.__stream is None:
                    stream = sys.stderr
                    if log_filename:
                        stream = open(log_filename, "w")
                    self.__stream = stream
                    return stream

        return stream

    def report(self, logger_name, show_stacktrace, levelname, message):
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


class _Logger(object):
    def __init__(self, name):
        self.name = name

    def critical(self, msg="", *args):
        if _log_config.log_level >= 0:
            self._report("CRITICAL", False, msg, *args)

    def exception(self, msg="", *args):
        if _log_config.log_level >= 0:
            self._report("EXCEPTION", True, msg, *args)

    def info(self, msg="", *args):
        if _log_config.log_level >= 1:
            self._report("INFO", False, msg, *args)

    def debug(self, msg="", *args):
        if _log_config.log_level >= 2:
            self._report("DEBUG", False, msg, *args)

    warn = warning = info
    error = exception

    def _report(self, levelname, show_stacktrace, msg="", *args):
        msg = _as_str(msg)
        if args:
            args = tuple(_as_str(arg) for arg in args)
            try:
                message = msg % args
            except:
                message = "%s - %s" % (msg, args)
        else:
            message = msg

        _log_config.report(self.name, show_stacktrace, levelname, message)


def get_log_level():
    return _log_config.log_level


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
    _log_config.log_filename = log_file


def configure_logger(postfix, log_level, log_file):
    """
    :param log_file:
        - If None, get target file from env var.
        - If empty string log to stderr.
    """

    if log_file:
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


def log_args_and_python(log, argv, version):
    log.debug("Arguments: %s", argv)
    log.debug(
        "Python: %s - lsp: %s - platform: %s - sys.prefix: %s - sys.executable: %s",
        sys.version,
        version,
        sys.platform,
        sys.prefix,
        sys.executable,
    )
