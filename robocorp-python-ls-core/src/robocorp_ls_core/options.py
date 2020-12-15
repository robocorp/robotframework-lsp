# i.e.: set to False only when debugging.
import os
import sys
from typing import Optional

USE_TIMEOUTS = True
if "GITHUB_WORKFLOW" not in os.environ:
    if "pydevd" in sys.modules:
        USE_TIMEOUTS = False

# If USE_TIMEOUTS is None, this timeout should be used.
NO_TIMEOUT = None

DEFAULT_TIMEOUT = 10


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


class BaseOptions(object):

    tcp: bool = False
    host: str = "127.0.0.1"
    port: int = 1456
    log_file: Optional[str] = None
    verbose: int = 0

    DEBUG_MESSAGE_MATCHERS = is_true_in_env(ENV_OPTION_LSP_DEBUG_MESSAGE_MATCHERS)
    DEBUG_PROCESS_ENVIRON = is_true_in_env(ENV_OPTION_LSP_DEBUG_PROCESS_ENVIRON)

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
