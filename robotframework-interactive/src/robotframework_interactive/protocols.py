import sys
import threading
from robocorp_ls_core.protocols import ActionResultDict

if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol


class IOnReadyCall(object):
    def __call__(self, interpreter: "IRobotFrameworkInterpreter"):
        pass


class IRobotFrameworkInterpreter(Protocol):
    def evaluate(self, code: str):
        pass

    def initialize(self, on_main_loop: IOnReadyCall):
        pass


class IMessage(Protocol):
    def __call__(self, interpreter: IRobotFrameworkInterpreter):
        pass

    event: threading.Event
    action_result_dict: ActionResultDict
