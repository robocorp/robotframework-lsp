import os
import enum
from typing import Optional

LOG_FILENAME: Optional[str] = os.getenv("ROBOTFRAMEWORK_DAP_LOG_FILENAME", None)

# Make sure that the log level is an int.
try:
    LOG_LEVEL = int(os.getenv("ROBOTFRAMEWORK_DAP_LOG_LEVEL", "0"))
except:
    LOG_LEVEL = 3

DEBUG = LOG_LEVEL > 1

TERMINAL_NONE = "none"
TERMINAL_INTEGRATED = "integrated"
TERMINAL_EXTERNAL = "external"

VALID_TERMINAL_OPTIONS = [TERMINAL_NONE, TERMINAL_INTEGRATED, TERMINAL_EXTERNAL]


STATE_RUNNING = "running"
STATE_PAUSED = "paused"

# See: StoppedEvent


class ReasonEnum(enum.Enum):
    REASON_NOT_STOPPED = "not_stopped"
    REASON_BREAKPOINT = "breakpoint"
    REASON_STEP = "step"
    REASON_PAUSE = "pause"
    REASON_EXCEPTION = "exception"


class StepEnum(enum.Enum):
    STEP_NONE = 0
    STEP_IN = 1
    STEP_NEXT = 2
    STEP_OUT = 3
