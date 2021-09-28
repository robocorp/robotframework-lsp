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


class EvaluateTextTypedDict(TypedDict):
    prefix: str  # The prefix added to the evaluation
    full_code: str  # The final code to be evaluated
    indent: str


class IOnReadyCall(object):
    def __call__(self, interpreter: "IRobotFrameworkInterpreter"):
        pass


class IRobotFrameworkInterpreter(Protocol):
    def compute_evaluate_text(
        self, code: str, target_type: str = "evaluate"
    ) -> EvaluateTextTypedDict:
        """
        :param target_type:
            'evaluate': means that the target is an evaluation with the given code.
                This implies that the current code must be changed to make sense
                in the given context.

            'completions': means that the target is a code-completion
                This implies that the current code must be changed to include
                all previous evaluation so that the code-completion contains
                the full information up to the current point.
        """

    def evaluate(self, code: str) -> ActionResultDict:
        pass

    def initialize(self, on_main_loop: IOnReadyCall):
        pass


class IMessage(Protocol):
    def __call__(self, interpreter: IRobotFrameworkInterpreter):
        pass

    event: threading.Event
    action_result_dict: ActionResultDict
