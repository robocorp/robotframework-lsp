from robocorp_ls_core.constants import *
from robocorp_ls_core.options import USE_TIMEOUTS
from typing import Optional

DEFAULT_COMPLETIONS_TIMEOUT: int = 4
if not USE_TIMEOUTS:
    DEFAULT_COMPLETIONS_TIMEOUT = 2 ** 30
