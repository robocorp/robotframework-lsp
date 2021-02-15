from robocorp_ls_core.constants import *
from robocorp_ls_core.options import USE_TIMEOUTS
from typing import Optional

DEFAULT_COMPLETIONS_TIMEOUT: int = 4
if not USE_TIMEOUTS:
    # A whole month of timeout seems good enough as a max.
    DEFAULT_COMPLETIONS_TIMEOUT = 60 * 60 * 24 * 30
