import os
import sys
from robotframework_ls.impl.robot_lsp_constants import (
    ENV_OPTION_ROBOT_LSP_DEBUG_PROCESS_ENVIRON,
    ENV_OPTION_ROBOT_LSP_DEBUG_MESSAGE_MATCHERS,
)


def _is_true_in_env(env_key):
    return os.getenv(env_key, "") in ("1", "True", "true")


class Options(object):

    tcp = False
    host = "127.0.0.1"
    port = 1456
    log_file = None
    verbose = 0

    DEBUG_MESSAGE_MATCHERS = _is_true_in_env(
        ENV_OPTION_ROBOT_LSP_DEBUG_MESSAGE_MATCHERS
    )
    DEBUG_PROCESS_ENVIRON = _is_true_in_env(ENV_OPTION_ROBOT_LSP_DEBUG_PROCESS_ENVIRON)

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
    options = Options()


# Note: set to False only when debugging.
USE_TIMEOUTS = True
if "GITHUB_WORKFLOW" not in os.environ:
    if "pydevd" in sys.modules:
        USE_TIMEOUTS = False

NO_TIMEOUT = None

DEFAULT_TIMEOUT = 10
