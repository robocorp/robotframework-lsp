import sys
import threading
from typing import Optional, Any


if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        def __init_subclass__(self, *args, **kwargs):
            pass


else:
    from typing import Protocol
    from typing import TypedDict


class ActionResultDict(TypedDict):
    success: bool
    message: Optional[
        str
    ]  # if success == False, this can be some message to show to the user
    result: Any


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
