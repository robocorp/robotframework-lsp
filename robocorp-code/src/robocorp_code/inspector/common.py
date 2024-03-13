import enum
from typing import Optional
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger("Inspector")

STATE_INITIALIZING = "initializing"
STATE_OPENED = "opened"
STATE_CLOSED = "closed"
STATE_PICKING = "picking"
STATE_NOT_PICKING = "notPicking"


class LogLevel(enum.Enum):
    INFO = 0
    DEBUG = 1
    WARNING = 2
    ERROR = 3


# log_call - decorator created to log a function's call and return value
def log_call(log_level: Optional[LogLevel] = None):
    logger = log.info
    if log_level:
        if log_level == LogLevel.INFO:
            logger = log.info
        if log_level == LogLevel.DEBUG:
            logger = log.debug
        if log_level == LogLevel.WARNING:
            logger = log.warn
        if log_level == LogLevel.ERROR:
            logger = log.error

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger(
                f"::: Calling {func.__name__} with: [args]",
                args,
                "[kwargs]",
                kwargs,
            )
            ret = func(*args, **kwargs)
            logger(
                f"::: Returning for {func.__name__} with: [args]",
                args,
                "[kwargs]",
                kwargs,
                "::: value :::",
                ret,
            )
            return ret

        return wrapper

    return decorator
