import os
from typing import Optional

LOG_FILENAME: Optional[str] = os.getenv("ROBOCORP_CODE_DAP_LOG_FILENAME", None)

# Make sure that the log level is an int.
try:
    LOG_LEVEL = int(os.getenv("ROBOCORP_CODE_DAP_LOG_LEVEL", "0"))
except:
    LOG_LEVEL = 3

DEBUG = LOG_LEVEL > 1

TERMINAL_NONE = "none"
TERMINAL_INTEGRATED = "integrated"
TERMINAL_EXTERNAL = "external"

VALID_TERMINAL_OPTIONS = [TERMINAL_NONE, TERMINAL_INTEGRATED, TERMINAL_EXTERNAL]

MAIN_THREAD_ID = 1
