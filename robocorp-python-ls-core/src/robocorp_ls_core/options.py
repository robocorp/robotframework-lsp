# i.e.: set to False only when debugging.
import os
import sys
from typing import Optional

USE_TIMEOUTS: bool = True
if "GITHUB_WORKFLOW" not in os.environ:
    if "pydevd" in sys.modules:
        USE_TIMEOUTS = False

# If USE_TIMEOUTS is None, this timeout should be used.
NO_TIMEOUT = None

DEFAULT_TIMEOUT = 15


def is_true_in_env(env_key):
    """
    :param str env_key:

    :return bool:
        True if the given key is to be considered to have a value which is to be
        considered True and False otherwise.
    """
    return os.getenv(env_key, "") in ("1", "True", "true")


# Options which must be set as environment variables.
ENV_OPTION_LSP_DEBUG_MESSAGE_MATCHERS = "LSP_DEBUG_MESSAGE_MATCHERS"

ENV_OPTION_LSP_DEBUG_PROCESS_ENVIRON = "LSP_DEBUG_PROCESS_ENVIRON"

ENV_OPTION_LSP_DEBUG_REMOTE_FS_MESSAGES = "LSP_DEBUG_FS_MESSAGES"

ENV_OPTION_LSP_DEBUG_CACHE_DEPS = "LSP_DEBUG_CACHE_DEPS"


class BaseOptions(object):
    tcp: bool = False
    host: str = "127.0.0.1"
    port: int = 1456
    log_file: Optional[str] = None
    verbose: int = 0

    DEBUG_MESSAGE_MATCHERS = is_true_in_env(ENV_OPTION_LSP_DEBUG_MESSAGE_MATCHERS)
    DEBUG_PROCESS_ENVIRON = is_true_in_env(ENV_OPTION_LSP_DEBUG_PROCESS_ENVIRON)
    DEBUG_REMOTE_FS_MESSAGES = is_true_in_env(ENV_OPTION_LSP_DEBUG_REMOTE_FS_MESSAGES)
    DEBUG_CACHE_DEPS = is_true_in_env(ENV_OPTION_LSP_DEBUG_CACHE_DEPS)

    HIDE_COMMAND_MESSAGES = set()

    if not DEBUG_REMOTE_FS_MESSAGES:
        HIDE_COMMAND_MESSAGES.add("ack_notify_on_any_change")
        HIDE_COMMAND_MESSAGES.add("notify_on_any_change")

    def __init__(self, args=None):
        """
        :param args:
            Instance with options to set (usually args from configparser).
        """
        if args is not None:
            for attr in dir(self):
                if not attr.startswith("_"):
                    if hasattr(args, attr):
                        setattr(self, attr, getattr(args, attr))


class Setup(object):
    # After parsing args it's replaced with the actual setup.
    options = BaseOptions()
