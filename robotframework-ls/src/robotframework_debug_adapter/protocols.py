# Hack so that we don't break the runtime on versions prior to Python 3.8.
import sys
from typing import TypeVar, List, Union, Any, Optional, Iterable
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StackFrame
from robocorp_ls_core.protocols import IFuture

if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol

T = TypeVar("T")
Y = TypeVar("Y", covariant=True)


class IEvaluationInfo(Protocol):
    future: IFuture[Any]


class IRobotBreakpoint(Protocol):
    # 1-based line for the breakpoint.
    lineno: int
    condition: Optional[str]
    hit_condition: Optional[int]
    log_message: Optional[str]

    hits: int


class IBusyWait(Protocol):
    before_wait: List[Any]
    waited: int
    proceeded: int

    def pre_wait(self) -> None:
        pass

    def wait(self) -> None:
        pass

    def proceed(self) -> None:
        pass


class IRobotDebugger(Protocol):
    busy_wait: IBusyWait

    def reset(self):
        pass

    def evaluate(
        self, frame_id: int, expression: str, context: str = "watch"
    ) -> IEvaluationInfo:
        """
        Asks something to be evaluated.

        This is an asynchronous operation and returns an _EvaluationInfo (to get
        the result, access _EvaluationInfo.future.result())
        """

    def step_continue(self) -> None:
        pass

    def step_in(self) -> None:
        pass

    def step_next(self) -> None:
        pass

    def step_out(self) -> None:
        pass

    def set_breakpoints(
        self,
        filename: str,
        breakpoints: Union[IRobotBreakpoint, Iterable[IRobotBreakpoint]],
    ) -> None:
        """
        :param str filename:
        :param list(RobotBreakpoint) breakpoints:
        """

    def get_frames(self, thread_id) -> Optional[List[StackFrame]]:
        pass

    def iter_frame_ids(self, thread_id) -> Iterable[int]:
        pass

    def get_current_thread_id(self, thread=None) -> int:
        pass

    def write_message(self, msg):
        pass

    def enable_no_debug_mode(self):
        pass


class INextId(Protocol):
    def __call__(self) -> T:
        pass
