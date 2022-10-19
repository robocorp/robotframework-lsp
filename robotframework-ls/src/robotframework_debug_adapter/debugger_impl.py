"""
Unfortunately right now Robotframework doesn't really provide the needed hooks
for a debugger, so, we monkey-patch internal APIs to gather the needed info.

More specifically:

    robot.running.steprunner.StepRunner - def run_step

    is patched so that we can stop when some line is about to be executed.
"""
import functools
from robotframework_debug_adapter import file_utils
import threading
from robotframework_debug_adapter.constants import (
    STATE_RUNNING,
    STATE_PAUSED,
    ReasonEnum,
    StepEnum,
)
import itertools
from functools import partial, lru_cache
import os.path
from robocorp_ls_core.robotframework_log import get_logger, get_log_level
from collections import namedtuple
import weakref
from robotframework_debug_adapter.protocols import (
    IRobotDebugger,
    INextId,
    IRobotBreakpoint,
    IBusyWait,
    IEvaluationInfo,
)
from typing import Optional, List, Iterable, Union, Any, Dict, FrozenSet
from robocorp_ls_core.basic import implements
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    StackFrame,
    Scope,
    Source,
    Variable,
    OutputEvent,
    OutputEventBody,
)

from robotframework_ls.impl.robot_constants import (
    get_builtin_variables,
    ROBOT_AND_TXT_FILE_EXTENSIONS,
)
import time


@lru_cache(None)
def get_builtin_normalized_names() -> FrozenSet[str]:
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    normalized = list()
    for k, _ in get_builtin_variables():
        normalized.append(normalize_robot_name(k))
    return frozenset(normalized)


log = get_logger(__name__)

next_id: INextId = partial(next, itertools.count(1))


class RobotBreakpoint(object):
    def __init__(
        self,
        lineno: int,
        condition: Optional[str] = None,
        hit_condition: Optional[int] = None,
        log_message: Optional[str] = None,
    ):
        """
        :param lineno:
            1-based line for the breakpoint.

        :param condition:
            If specified, the breakpoint will only be hit if the condition
            evaluates to True.

        :param hit_condition:
            If specified, the breakpoint will only be hit after it hits the
            specified number of times.

        :param log_message:
            If specified, the breakpoint will not actually break, it'll just
            print the given message instead of breaking.
        """
        self.lineno = lineno
        self.condition = condition
        if hit_condition is not None:
            hit_condition = int(hit_condition)
        self.hit_condition = hit_condition
        self.log_message = log_message
        self.hits = 0


class BusyWait(object):
    def __init__(self):
        self.before_wait = []
        self.waited = 0
        self.proceeded = 0
        self._condition = threading.Condition()

    @implements(IBusyWait.pre_wait)
    def pre_wait(self):
        for c in self.before_wait:
            c()

    @implements(IBusyWait.wait)
    def wait(self):
        self.waited += 1
        with self._condition:
            self._condition.wait()

    @implements(IBusyWait.proceed)
    def proceed(self):
        self.proceeded += 1
        with self._condition:
            self._condition.notify_all()


class _BaseObjectToDAP(object):
    """
    Base class for classes which converts some object to the DAP.
    """

    def compute_as_dap(self) -> List[Variable]:
        return []


class _ArgsAsDAP(_BaseObjectToDAP):
    """
    Provides args as DAP variables.
    """

    def __init__(self, keyword_args):
        self._keyword_args = keyword_args

    def compute_as_dap(self) -> List[Variable]:
        from robotframework_debug_adapter.safe_repr import SafeRepr

        lst = []
        safe_repr = SafeRepr()
        for i, arg in enumerate(self._keyword_args):
            lst.append(Variable("Arg %s" % (i,), safe_repr(arg), variablesReference=0))
        return lst


class _NonBuiltinVariablesAsDAP(_BaseObjectToDAP):
    """
    Provides variables as DAP variables.
    """

    def __init__(self, variables):
        self._variables = variables
        self._builtins = get_builtin_normalized_names()

    def compute_as_dap(self) -> List[Variable]:
        from robotframework_debug_adapter.safe_repr import SafeRepr

        variables = self._variables
        as_dct = variables.as_dict()
        lst = []
        safe_repr = SafeRepr()

        for key, val in as_dct.items():
            if self._accept(key):
                lst.append(
                    Variable(safe_repr(key), safe_repr(val), variablesReference=0)
                )
        return lst

    def _accept(self, k: str) -> bool:
        from robotframework_ls.impl.variable_resolve import normalize_variable_name

        if normalize_variable_name(k) in self._builtins:
            return False
        else:
            return True


class _BuiltinsAsDAP(_NonBuiltinVariablesAsDAP):
    """
    Provides variables as DAP variables.
    """

    def _accept(self, k: str) -> bool:
        return not _NonBuiltinVariablesAsDAP._accept(self, k)


class _BaseFrameInfo(object):
    @property
    def dap_frame(self):
        raise NotImplementedError("Not implemented in: %s" % (self.__class__,))

    def get_scopes(self) -> List[Scope]:
        raise NotImplementedError("Not implemented in: %s" % (self.__class__,))

    def get_type_name(self):
        raise NotImplementedError("Not implemented in: %s" % (self.__class__,))


class _SuiteFrameInfo(_BaseFrameInfo):
    def __init__(self, stack_list, dap_frame):
        self._stack_list = weakref.ref(stack_list)
        self._dap_frame = dap_frame

    @property
    def dap_frame(self):
        return self._dap_frame

    def get_scopes(self) -> List[Scope]:
        return []

    def get_type_name(self):
        return "Suite"


class _TestFrameInfo(_BaseFrameInfo):
    def __init__(self, stack_list, dap_frame):
        self._stack_list = weakref.ref(stack_list)
        self._dap_frame = dap_frame

    @property
    def dap_frame(self):
        return self._dap_frame

    def get_scopes(self) -> List[Scope]:
        return []

    def get_type_name(self):
        return "Test"


class _LogFrameInfo(_BaseFrameInfo):
    def __init__(self, stack_list, dap_frame):
        self._stack_list = weakref.ref(stack_list)
        self._dap_frame = dap_frame

    @property
    def dap_frame(self):
        return self._dap_frame

    def get_scopes(self) -> List[Scope]:
        return []

    def get_type_name(self):
        return "Log"


class _KeywordFrameInfo(_BaseFrameInfo):
    def __init__(
        self, stack_list, dap_frame, name, lineno, args, variables, execution_context
    ):
        self._stack_list = weakref.ref(stack_list)
        self._dap_frame = dap_frame
        self._name = name
        self._lineno = lineno
        self._scopes = None
        self._args = args
        self._variables = variables
        self._execution_context = execution_context

    @property
    def name(self):
        return self._name

    @property
    def lineno(self):
        return self._lineno

    @property
    def variables(self):
        return self._variables

    @property
    def execution_context(self):
        return self._execution_context

    @property
    def dap_frame(self):
        return self._dap_frame

    def get_type_name(self):
        return "Keyword"

    def get_scopes(self) -> List[Scope]:
        if self._scopes is not None:
            return self._scopes
        stack_list = self._stack_list()
        if stack_list is None:
            return []

        locals_variables_reference: int = next_id()
        vars_variables_reference: int = next_id()
        builtions_variables_reference: int = next_id()
        scopes = [
            Scope("Variables", vars_variables_reference, expensive=False),
            Scope(
                "Arguments",
                locals_variables_reference,
                expensive=False,
                presentationHint="locals",
            ),
            Scope("Builtins", builtions_variables_reference, expensive=False),
        ]

        args = self._args
        stack_list.register_variables_reference(
            locals_variables_reference, _ArgsAsDAP(args)
        )
        # ctx.namespace.get_library_instances()

        stack_list.register_variables_reference(
            vars_variables_reference, _NonBuiltinVariablesAsDAP(self._variables)
        )
        stack_list.register_variables_reference(
            builtions_variables_reference, _BuiltinsAsDAP(self._variables)
        )
        self._scopes = scopes
        return self._scopes


class _StackInfo(object):
    """
    This is the information for the stacks available when we're stopped in a
    breakpoint.
    """

    def __init__(self):
        self._frame_id_to_frame_info: Dict[int, _BaseFrameInfo] = {}
        self._dap_frames = []
        self._ref_id_to_children = {}

    def iter_frame_ids(self) -> Iterable[int]:
        """
        Access to list(int) where iter_frame_ids[0] is the current frame
        where we're stopped (topmost frame).
        """
        return (x.id for x in self._dap_frames)

    def register_variables_reference(self, variables_reference, children):
        self._ref_id_to_children[variables_reference] = children

    def add_keyword_entry_stack(
        self, name, lineno, filename: str, args, variables, execution_context
    ) -> int:
        frame_id: int = next_id()
        dap_frame = StackFrame(
            frame_id,
            name=name,
            line=lineno or 1,
            column=0,
            source=Source(name=os.path.basename(filename), path=filename),
        )
        self._dap_frames.append(dap_frame)
        self._frame_id_to_frame_info[frame_id] = _KeywordFrameInfo(
            self, dap_frame, name, lineno, args, variables, execution_context
        )
        return frame_id

    def add_suite_entry_stack(self, name: str, filename: str) -> int:
        frame_id: int = next_id()
        dap_frame = StackFrame(
            frame_id,
            name=name,
            line=1,
            column=0,
            source=Source(name=os.path.basename(filename), path=filename),
        )
        self._dap_frames.append(dap_frame)
        self._frame_id_to_frame_info[frame_id] = _SuiteFrameInfo(self, dap_frame)
        return frame_id

    def add_test_entry_stack(self, name: str, filename: str, lineno: int) -> int:
        from robocorp_ls_core.debug_adapter_core.dap import dap_schema

        frame_id: int = next_id()
        dap_frame = dap_schema.StackFrame(
            frame_id,
            name=name,
            line=lineno,
            column=0,
            source=dap_schema.Source(name=os.path.basename(filename), path=filename),
        )
        self._dap_frames.append(dap_frame)
        self._frame_id_to_frame_info[frame_id] = _TestFrameInfo(self, dap_frame)
        return frame_id

    def add_log_entry_stack(self, name: str, filename: str, lineno: int) -> int:
        from robocorp_ls_core.debug_adapter_core.dap import dap_schema

        frame_id: int = next_id()
        dap_frame = dap_schema.StackFrame(
            frame_id,
            name=name,
            line=lineno,
            column=0,
            source=dap_schema.Source(name=os.path.basename(filename), path=filename),
        )
        self._dap_frames.append(dap_frame)
        self._frame_id_to_frame_info[frame_id] = _LogFrameInfo(self, dap_frame)
        return frame_id

    @property
    def dap_frames(self) -> List[StackFrame]:
        """
        Access to list(StackFrame) where dap_frames[0] is the current frame
        where we're stopped (topmost frame).
        """
        return self._dap_frames

    def get_scopes(self, frame_id):
        frame_info = self._frame_id_to_frame_info.get(frame_id)
        if frame_info is None:
            return None
        return frame_info.get_scopes()

    def get_variables(self, variables_reference):
        lst = self._ref_id_to_children.get(variables_reference)
        if lst is not None:
            if isinstance(lst, _BaseObjectToDAP):
                lst = lst.compute_as_dap()
        return lst


_StepEntry = namedtuple(
    "_StepEntry", "name, lineno, source, args, variables, entry_type, execution_context"
)
_SuiteEntry = namedtuple("_SuiteEntry", "name, source, entry_type")
_TestEntry = namedtuple("_TestEntry", "name, source, lineno, entry_type")
_LogEntry = namedtuple("_LogEntry", "name, source, lineno, entry_type")


class InvalidFrameIdError(Exception):
    pass


class InvalidFrameTypeError(Exception):
    pass


class UnableToEvaluateError(Exception):
    pass


class EvaluationResult(Exception):
    def __init__(self, result):
        self.result = result


class _EvaluationInfo(object):
    def __init__(self, frame_id: int, expression: str, context: str):
        from concurrent import futures
        from robocorp_ls_core.protocols import IFuture

        self.frame_id = frame_id
        self.expression = expression
        self.context = context
        self.future: IFuture[Any] = futures.Future()

    def _do_eval(self, debugger_impl):
        frame_id = self.frame_id
        stack_info = debugger_impl._get_stack_info_from_frame_id(frame_id)

        if stack_info is None:
            raise InvalidFrameIdError(
                "Unable to find frame id for evaluation: %s" % (frame_id,)
            )

        dap_frames = stack_info.dap_frames
        if not dap_frames:
            raise InvalidFrameIdError("No frames for evaluation.")

        top_frame_id = dap_frames[0].id
        if top_frame_id != frame_id:
            if get_log_level() >= 2:
                log.debug(
                    "Unable to evaluate.\nFrame id for evaluation: %r\nTop frame id: %r.\nDAP frames:\n%s",
                    frame_id,
                    top_frame_id,
                    "\n".join(x.to_json() for x in dap_frames),
                )

            raise UnableToEvaluateError(
                "Keyword calls may only be evaluated at the topmost frame."
            )

        info = stack_info._frame_id_to_frame_info.get(frame_id)
        if info is None:
            raise InvalidFrameIdError(
                "Unable to find frame info for evaluation: %s" % (frame_id,)
            )

        if isinstance(info, _LogFrameInfo):
            if len(dap_frames) < 2:
                raise InvalidFrameIdError(
                    "Unable to evaluate in Log frame entry without a parent."
                )

            else:
                frame_id = dap_frames[1].id
                info = stack_info._frame_id_to_frame_info.get(frame_id)
                if info is None:
                    raise InvalidFrameIdError(
                        "Unable to find frame info for evaluation: %s" % (frame_id,)
                    )

        if not isinstance(info, _KeywordFrameInfo):
            raise InvalidFrameTypeError(
                "Can only evaluate at a Keyword context (current context: %s)"
                % (info.get_type_name(),)
            )
        log.info("Doing evaluation in the Keyword context: %s", info.name)

        from robotframework_ls.impl.text_utilities import is_variable_text

        from robot.libraries.BuiltIn import BuiltIn  # type: ignore
        from robot.api import get_model  # type: ignore
        from robotframework_ls.impl import ast_utils
        from robotframework_ls.impl.robot_localization import LocalizationInfo

        # We can't really use
        # BuiltIn().evaluate(expression, modules, namespace)
        # because we can't set the variable_store used with it
        # (it always uses the latest).

        variable_store = info.variables.store

        if is_variable_text(self.expression):
            try:
                value = variable_store[self.expression[2:-1]]
            except Exception:
                pass
            else:
                return EvaluationResult(value)

        if self.context == "hover":
            try:
                ctx = info.execution_context
                return EvaluationResult(
                    ctx.namespace.get_runner(self.expression).longname
                )
            except:
                log.exception("Error on hover evaluation: %s", self.expression)
                return EvaluationResult("")

        # Do we want this?
        # from robot.variables.evaluation import evaluate_expression
        # try:
        #     result = evaluate_expression(self.expression, variable_store)
        # except Exception:
        #     log.exception()
        # else:
        #     return EvaluationResult(result)

        # Try to check if it's a KeywordCall.
        s = """
*** Test Cases ***
Evaluation
    %s
""" % (
            self.expression,
        )
        model = get_model(s)
        ast_utils.set_localization_info_in_model(model, LocalizationInfo("en"))
        usage_info = list(
            ast_utils.iter_keyword_usage_tokens(model, collect_args_as_keywords=False)
        )
        if len(usage_info) == 1:
            usage = next(iter(usage_info))
            node = usage.node
            name = usage.name

            assign = node.assign
            from robot.running import Keyword

            kw = Keyword(name, args=node.args, assign=assign)
            ctx = info.execution_context
            return EvaluationResult(kw.run(ctx))

        raise UnableToEvaluateError("Unable to evaluate: %s" % (self.expression,))

    def evaluate(self, debugger_impl):
        """
        :param _RobotDebuggerImpl debugger_impl:
        """
        try:
            r = self._do_eval(debugger_impl)
            self.future.set_result(r.result)
        except Exception as e:
            if get_log_level() >= 2:
                log.exception("Error evaluating: %s", (self.expression,))
            self.future.set_exception(e)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IEvaluationInfo = check_implements(self)


class _RobotDebuggerImpl(object):
    """
    This class provides the main API to deal with debugging
    Robot Framework.
    """

    def __init__(self):
        self.reset()

    @implements(IRobotDebugger.reset)
    def reset(self):
        from collections import deque
        from robotframework_debug_adapter._ignore_failures_in_stack import (
            IgnoreFailuresInStack,
        )

        self._filename_to_line_to_breakpoint = {}
        self.busy_wait = BusyWait()

        self._run_state = STATE_RUNNING
        self._step_cmd: StepEnum = StepEnum.STEP_NONE
        self._reason: ReasonEnum = ReasonEnum.REASON_NOT_STOPPED
        self._next_id = next_id
        self._stack_ctx_entries_deque = deque()
        self._stop_on_stack_len = 0

        self._tid_to_stack_info: Dict[int, _StackInfo] = {}
        self._frame_id_to_tid = {}
        self._evaluations = []
        self._skip_breakpoints = 0

        self._exc_name = None
        self._exc_description = None
        self._last_time_time_output_event = 0

        def is_true_in_env(key):
            return os.getenv(key, "0").lower() in (
                "1",
                "True",
                "true",
            )

        self.break_on_log_failure = is_true_in_env("RFLS_BREAK_ON_FAILURE")
        self.break_on_log_error = is_true_in_env("RFLS_BREAK_ON_ERROR")
        self._ignore_failures_in_stack = IgnoreFailuresInStack()

    def enable_no_debug_mode(self):
        self._skip_breakpoints += 1
        self.break_on_log_failure = False
        self.break_on_log_error = False

    def write_message(self, msg):
        log.critical(
            "Message: %s not sent!\nExpected _RobotDebuggerImpl.write_message to be replaced to the actual implementation!",
            msg,
        )
        raise AssertionError("Error")

    @property
    def stop_reason(self) -> ReasonEnum:
        return self._reason

    @property
    def exc_name(self) -> Optional[str]:
        return self._exc_name

    @property
    def exc_description(self) -> Optional[str]:
        return self._exc_description

    def _get_stack_info_from_frame_id(self, frame_id) -> Optional[_StackInfo]:
        thread_id = self._frame_id_to_tid.get(frame_id)
        if thread_id is not None:
            return self._get_stack_info(thread_id)
        return None

    def _get_stack_info(self, thread_id) -> Optional[_StackInfo]:
        return self._tid_to_stack_info.get(thread_id)

    def get_frames(self, thread_id) -> Optional[List[StackFrame]]:
        stack_info = self._get_stack_info(thread_id)
        if not stack_info:
            return None
        return stack_info.dap_frames

    def iter_frame_ids(self, thread_id) -> Iterable[int]:
        stack_info = self._get_stack_info(thread_id)
        if not stack_info:
            return ()
        return stack_info.iter_frame_ids()

    def get_scopes(self, frame_id) -> Optional[List[Scope]]:
        tid = self._frame_id_to_tid.get(frame_id)
        if tid is None:
            return None

        stack_info = self._get_stack_info(tid)
        if not stack_info:
            return None
        return stack_info.get_scopes(frame_id)

    def get_variables(self, variables_reference):
        for stack_list in list(self._tid_to_stack_info.values()):
            variables = stack_list.get_variables(variables_reference)
            if variables is not None:
                return variables
        return None

    def _get_filename(self, obj, msg) -> str:
        try:
            source = obj.source
            if source is None:
                return "None"

            filename, _changed = file_utils.norm_file_to_client(source)
        except:
            filename = "<Unable to get %s filename>" % (msg,)
            log.exception(filename)

        return filename

    def _create_stack_info(self, thread_id: int):
        stack_info = _StackInfo()

        for entry in reversed(self._stack_ctx_entries_deque):
            try:
                if entry.__class__ == _StepEntry:
                    name = entry.name
                    lineno = entry.lineno
                    variables = entry.variables
                    args = entry.args
                    execution_context = entry.execution_context
                    filename = self._get_filename(entry, "Keyword")

                    frame_id = stack_info.add_keyword_entry_stack(
                        name, lineno, filename, args, variables, execution_context
                    )

                elif entry.__class__ == _SuiteEntry:
                    name = "TestSuite: %s" % (entry.name,)
                    filename = self._get_filename(entry, "TestSuite")

                    frame_id = stack_info.add_suite_entry_stack(name, filename)

                elif entry.__class__ == _TestEntry:
                    name = "TestCase: %s" % (entry.name,)
                    filename = self._get_filename(entry, "TestCase")

                    frame_id = stack_info.add_test_entry_stack(
                        name, filename, entry.lineno
                    )

                elif entry.__class__ == _LogEntry:
                    name = "Log (%s)" % (entry.name,)
                    filename = self._get_filename(entry, "Log")

                    frame_id = stack_info.add_log_entry_stack(
                        name, filename, entry.lineno
                    )
            except:
                log.exception("Error creating stack trace.")

        for frame_id in stack_info.iter_frame_ids():
            self._frame_id_to_tid[frame_id] = thread_id

        self._tid_to_stack_info[thread_id] = stack_info

    def _dispose_stack_info(self, thread_id):
        stack_list = self._tid_to_stack_info.pop(thread_id)
        for frame_id in stack_list.iter_frame_ids():
            self._frame_id_to_tid.pop(frame_id)

    def get_current_thread_id(self, thread=None):
        from robotframework_debug_adapter.vendored import force_pydevd  # noqa
        from _pydevd_bundle.pydevd_constants import get_current_thread_id

        if thread is None:
            thread = threading.current_thread()
        return get_current_thread_id(thread)

    def wait_suspended(self, reason: ReasonEnum) -> None:
        thread_id = self.get_current_thread_id()

        if self._exc_name or self._exc_description:
            log.info(
                "wait_suspended. Reason: %s. Exc name: %s. Exc description: %s",
                reason,
                self._exc_name,
                self._exc_description,
            )
        else:
            log.info("wait_suspended. Reason: %s", reason)
        self._create_stack_info(thread_id)
        try:
            self._run_state = STATE_PAUSED
            self._reason = reason

            self.busy_wait.pre_wait()

            while self._run_state == STATE_PAUSED:
                self.busy_wait.wait()

                evaluations = self._evaluations
                self._evaluations = []

                for evaluation in evaluations:  #: :type evaluation: _EvaluationInfo
                    self._skip_breakpoints += 1
                    try:
                        evaluation.evaluate(self)
                    finally:
                        self._skip_breakpoints -= 1

            if self._step_cmd == StepEnum.STEP_NEXT:
                self._stop_on_stack_len = len(self._stack_ctx_entries_deque)
                if self._stop_on_stack_len:
                    if self._is_control_step(
                        self._stack_ctx_entries_deque[-1].entry_type
                    ):
                        self._stop_on_stack_len += 1

            elif self._step_cmd == StepEnum.STEP_OUT:
                self._stop_on_stack_len = len(self._stack_ctx_entries_deque) - 1

        finally:
            self._reason = ReasonEnum.REASON_NOT_STOPPED
            self._dispose_stack_info(thread_id)

    @implements(IRobotDebugger.evaluate)
    def evaluate(
        self, frame_id: int, expression: str, context: str = "watch"
    ) -> IEvaluationInfo:
        """
        Asks something to be evaluated.

        This is an asynchronous operation and returns an _EvaluationInfo (to get
        the result, access _EvaluationInfo.future.result())
        """
        evaluation_info = _EvaluationInfo(frame_id, expression, context)
        self._evaluations.append(evaluation_info)
        self.busy_wait.proceed()
        return evaluation_info

    @implements(IRobotDebugger.step_continue)
    def step_continue(self) -> None:
        self._step_cmd = StepEnum.STEP_NONE
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    @implements(IRobotDebugger.step_in)
    def step_in(self) -> None:
        self._step_cmd = StepEnum.STEP_IN
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    @implements(IRobotDebugger.step_next)
    def step_next(self) -> None:
        self._step_cmd = StepEnum.STEP_NEXT
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    @implements(IRobotDebugger.step_out)
    def step_out(self) -> None:
        self._step_cmd = StepEnum.STEP_OUT
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    @implements(IRobotDebugger.set_breakpoints)
    def set_breakpoints(
        self,
        filename: str,
        breakpoints: Union[IRobotBreakpoint, Iterable[IRobotBreakpoint]],
    ) -> None:
        iter_in: Any
        if isinstance(breakpoints, (list, tuple, set)):
            iter_in = breakpoints
        else:
            iter_in = [breakpoints]
        filename = file_utils.get_abs_path_real_path_and_base_from_file(filename)[1]
        line_to_bp = {}

        for bp in iter_in:
            log.info("Set breakpoint in %s: %s", filename, bp.lineno)
            line_to_bp[bp.lineno] = bp
        self._filename_to_line_to_breakpoint[filename] = line_to_bp

    # ------------------------------------------------- RobotFramework listeners

    # 4.0 versions where the lineno is available on the V2 listener
    def start_keyword_v2(self, _name, attributes):
        from robot.running.context import EXECUTION_CONTEXTS

        ctx = EXECUTION_CONTEXTS.current
        lineno = attributes["lineno"]
        source = attributes["source"]
        name = attributes["kwname"]
        args = attributes["args"]
        entry_type = attributes.get("type", "KEYWORD")
        if attributes.get("status") == "NOT RUN":
            return
        if not args:
            args = []
        self._before_run_step(ctx, name, entry_type, lineno, source, args)

    # 4.0 versions where the lineno is available on the V2 listener
    def end_keyword_v2(self, name, attributes):

        if attributes.get("status") == "NOT RUN":
            return

        self._after_run_step()

    # 3.x versions where the lineno is NOT available on the V2 listener
    def before_control_flow_stmt(self, control_flow_stmt, ctx, *args, **kwargs):
        name = ""
        try:
            if control_flow_stmt.type == "IF/ELSE ROOT":
                name = control_flow_stmt.body[0].condition

            elif control_flow_stmt.type == "KEYWORD":
                name = control_flow_stmt.name

            else:
                name = str(control_flow_stmt).strip()
        except:
            pass

        if not name:
            name = control_flow_stmt.__class__.__name__

        try:
            lineno = control_flow_stmt.lineno
            source = control_flow_stmt.source
        except AttributeError:
            return

        try:
            args = control_flow_stmt.args
        except AttributeError:
            args = []
        entry_type = "KEYWORD"
        self._before_run_step(ctx, name, entry_type, lineno, source, args)

    # 3.x versions where the lineno is NOT available on the V2 listener
    def after_control_flow_stmt(self, control_flow_stmt, ctx, *args, **kwargs):
        self._after_run_step()

    def before_keyword_runner(self, runner, step, *args, **kwargs):
        name = ""
        try:
            name = step.name
        except:
            pass
        if not name:
            name = step.__class__.__name__
        try:
            lineno = step.lineno
            source = step.source
        except AttributeError:
            return
        try:
            args = step.args
        except AttributeError:
            args = []
        ctx = runner._context
        entry_type = "KEYWORD"
        self._before_run_step(ctx, name, entry_type, lineno, source, args)

    def after_keyword_runner(self, runner, step, *args, **kwargs):
        self._after_run_step()

    # 3.x versions where the lineno is NOT available on the V2 listener
    def before_run_step(self, step_runner, step, name=None):
        try:
            name = str(step).strip()
            if not name:
                name = step.__class__.__name__
        except:
            name = "<Unable to get keyword name>"
        try:
            lineno = step.lineno
            source = step.source
        except AttributeError:
            return
        try:
            args = step.args
        except AttributeError:
            args = []
        ctx = step_runner._context
        entry_type = "KEYWORD"
        self._before_run_step(ctx, name, entry_type, lineno, source, args)

    # 3.x versions where the lineno is NOT available on the V2 listener
    def after_run_step(self, step_runner, step, name=None):
        self._after_run_step()

    def _is_control_step(self, entry_type):
        return entry_type in (
            "ELSE IF",
            "ELSE",
            "EXCEPT",
            "FINALLY",
            "FOR ITERATION",
            "FOR",
            "IF",
            "ITERATION",
            "TRY",
            "WHILE",
        )

    def _before_run_step(self, ctx, name, entry_type, lineno, source, args):
        if entry_type == "KEYWORD":
            self._ignore_failures_in_stack.push(name)

        if not name:
            name = entry_type

        if self._is_control_step(entry_type):
            self._stop_on_stack_len += 1

        if source is None or lineno is None:
            # RunKeywordIf doesn't have a source, so, just show the caller source.
            for entry in reversed(self._stack_ctx_entries_deque):
                if source is None:
                    source = entry.source
                if lineno is None:
                    lineno = entry.lineno
                break

        if not source:
            return
        if not source.endswith(ROBOT_AND_TXT_FILE_EXTENSIONS):
            robot_init = os.path.join(source, "__init__.robot")
            if os.path.exists(robot_init):
                source = robot_init
        self._stack_ctx_entries_deque.append(
            _StepEntry(
                name, lineno, source, args, ctx.variables.current, entry_type, ctx
            )
        )
        if self._skip_breakpoints:
            return

        source = file_utils.get_abs_path_real_path_and_base_from_file(source)[1]
        log.debug(
            "run_step %s, %s - step: %s - %s\n", name, lineno, self._step_cmd, source
        )
        lines = self._filename_to_line_to_breakpoint.get(source)

        stop_reason: Optional[ReasonEnum] = None
        step_cmd = self._step_cmd
        if lines:
            bp: Optional[IRobotBreakpoint] = lines.get(lineno)
            if bp:
                # Mark it to stop and then go over exclusions based on condition
                # and hit_condition.
                stop_reason = ReasonEnum.REASON_BREAKPOINT

                if bp.condition:
                    try:
                        from robot.variables.evaluation import (
                            evaluate_expression,
                        )  # noqa

                        curr_vars = ctx.variables.current
                        hit = bool(
                            evaluate_expression(
                                curr_vars.replace_string(bp.condition), curr_vars.store
                            )
                        )
                        if not hit:
                            log.debug(
                                "Breakpoint at %s (%s) skipped (%s evaluated to False)",
                                source,
                                lineno,
                                bp.condition,
                            )
                            stop_reason = None
                    except:
                        log.exception("Error evaluating: %s", bp.condition)

                if stop_reason is not None and bp.hit_condition:
                    bp.hits += 1
                    if bp.hits != bp.hit_condition:
                        log.debug(
                            "Breakpoint at %s (%s) skipped (hit condition: %s evaluated to False)",
                            source,
                            lineno,
                            bp.hit_condition,
                        )
                        stop_reason = None

                if stop_reason is not None:
                    if bp.log_message:
                        curr_vars = ctx.variables.current
                        try:
                            message = curr_vars.replace_string(bp.log_message)
                        except Exception as e:
                            message = (
                                f"Error evaluating: {bp.log_message}.\nError: {e}\n"
                            )

                        if not message.endswith(("\n", "\r")):
                            message += "\n"

                        self.write_message(
                            OutputEvent(
                                body=OutputEventBody(
                                    source=Source(path=source),
                                    line=lineno,
                                    output=message,
                                    category="console",
                                )
                            )
                        )
                        log.debug(
                            "Breakpoint at %s (%s) skipped (due to being a log message breakpoint).",
                            source,
                            lineno,
                        )
                        stop_reason = None

        if stop_reason is None and step_cmd is not None:
            if step_cmd == StepEnum.STEP_IN:
                stop_reason = ReasonEnum.REASON_STEP

            elif step_cmd in (StepEnum.STEP_NEXT, StepEnum.STEP_OUT):
                if len(self._stack_ctx_entries_deque) <= self._stop_on_stack_len:
                    stop_reason = ReasonEnum.REASON_STEP

        if stop_reason is not None:
            self.wait_suspended(stop_reason)

    def _after_run_step(self):
        entry = self._stack_ctx_entries_deque.pop()

        if entry.entry_type == "KEYWORD":
            self._ignore_failures_in_stack.pop()

        if self._is_control_step(entry.entry_type):
            self._stop_on_stack_len -= 1

    def start_suite(self, data, result):
        self._stack_ctx_entries_deque.append(
            _SuiteEntry(data.name, data.source, "SUITE")
        )

    def end_suite(self, data, result):
        self._stack_ctx_entries_deque.pop()

    def start_test(self, data, result):
        self._stack_ctx_entries_deque.append(
            _TestEntry(data.name, data.source, data.lineno, "TEST")
        )

    def end_test(self, data, result):
        self._stack_ctx_entries_deque.pop()

    def log_message(self, message, skip_error=True):
        from robotframework_debug_adapter.message_utils import (
            extract_source_and_line_from_message,
        )

        level = message.level
        if level not in ("ERROR", "FAIL", "WARN", "INFO"):
            # Exclude TRACE/DEBUG/HTML for now (we could make that configurable...)
            return

        if skip_error and level in ("ERROR",):
            # We do this because in RF all the calls to 'log_message'
            # also generate a call to 'message', so, we want to skip
            # one of those (but note that the other way around isn't true
            # and some errors such as import errors are only reported
            # in 'message' and not 'log_message').
            return

        # When debugging show any message in the console (if possible with the
        # current keyword as the source).
        try:
            source = None
            lineno = None
            path = None

            source_and_line = extract_source_and_line_from_message(message.message)

            if source_and_line is not None:
                path, lineno = source_and_line
                source = Source(path=path)
            else:
                if self._stack_ctx_entries_deque:
                    lineno = 0
                    step_entry: _StepEntry = self._stack_ctx_entries_deque[-1]
                    path = step_entry.source
                    source = Source(path=path)
                    try:
                        lineno = step_entry.lineno
                    except AttributeError:
                        pass

            if not self._last_time_time_output_event:
                self._last_time_time_output_event = time.time()
                delta = 0
            else:
                curr_time = time.time()
                delta = curr_time - self._last_time_time_output_event
                self._last_time_time_output_event = curr_time

            level = self._translate_level(level)

            delta_str: str = f"{delta:.2f}"
            if delta_str != "0.00":
                output = f"[{level} (+{delta_str}s)] {message.message}\n"
            else:
                output = f"[{level}] {message.message}\n"

            self.write_message(
                OutputEvent(
                    body=OutputEventBody(
                        source=source,
                        line=lineno,
                        output=output,
                        category="console",
                    )
                )
            )
            self._break_on_log_or_system_message(message, path, lineno)
        except:
            log.exception("Error handling log_message.")

    @classmethod
    def _translate_level(cls, level):
        if level not in ("ERROR", "FAIL", "WARN"):
            level = level.lower()
        return level

    def message(self, message):
        if message.level in ("FAIL", "ERROR"):
            return self.log_message(message, skip_error=False)

    def _break_on_log_or_system_message(self, message, path, lineno):
        stop_reason = None
        if message.level == "FAIL":
            if self.break_on_log_failure:
                stop_reason = ReasonEnum.REASON_EXCEPTION
                exc_name = "Suspended due to logged failure: "

        elif message.level == "ERROR":
            if self.break_on_log_error:
                stop_reason = ReasonEnum.REASON_EXCEPTION
                exc_name = "Suspended due to logged error: "

        if stop_reason is not None:
            if self._ignore_failures_in_stack.ignore():
                return

            if path is not None and lineno is not None:
                entry = _LogEntry(message.level, path, lineno, "LOG")
                self._stack_ctx_entries_deque.append(entry)

            self._exc_name = exc_name + message.message
            self._exc_description = message.message
            try:
                self.wait_suspended(stop_reason)
            finally:
                self._exc_name = None
                self._exc_description = None

                if entry is not None:
                    self._stack_ctx_entries_deque.pop()


def _patch(
    execution_context_cls, impl, method_name, call_before_method, call_after_method
):

    original_method = getattr(execution_context_cls, method_name)

    @functools.wraps(original_method)
    def new_method(*args, **kwargs):
        call_before_method(*args, **kwargs)
        try:
            ret = original_method(*args, **kwargs)
        finally:
            call_after_method(*args, **kwargs)
        return ret

    setattr(execution_context_cls, method_name, new_method)


class _DebuggerHolder(object):
    _dbg: Optional[IRobotDebugger] = None


def set_global_robot_debugger(dbg: IRobotDebugger):
    _DebuggerHolder._dbg = dbg


def get_global_robot_debugger() -> Optional[IRobotDebugger]:
    return _DebuggerHolder._dbg


def _apply_monkeypatching_latest(impl):
    from robot.running.model import If, For
    from robot.running.bodyrunner import KeywordRunner

    _patch(
        KeywordRunner,
        impl,
        "run",
        impl.before_keyword_runner,
        impl.after_keyword_runner,
    )
    _patch(If, impl, "run", impl.before_control_flow_stmt, impl.after_control_flow_stmt)
    _patch(
        For, impl, "run", impl.before_control_flow_stmt, impl.after_control_flow_stmt
    )


def _apply_monkeypatching_before_4_b_2(impl):
    from robot.running.steprunner import (  # type: ignore
        StepRunner,  #  @UnresolvedImport
    )

    _patch(StepRunner, impl, "run_step", impl.before_run_step, impl.after_run_step)

    try:
        from robot.running.model import For  # type: ignore # @UnresolvedImport

        _patch(
            For,
            impl,
            "run",
            impl.before_control_flow_stmt,
            impl.after_control_flow_stmt,
        )
    except:
        # This may not be the same on older versions...
        pass

    try:
        from robot.running.model import If  # type: ignore # @UnresolvedImport

        _patch(
            If, impl, "run", impl.before_control_flow_stmt, impl.after_control_flow_stmt
        )
    except:
        # This may not be the same on older versions...
        pass


def install_robot_debugger() -> IRobotDebugger:
    """
    Installs the robot debugger and registers it where needed. If a debugger
    is currently installed, resets it (in this case, any existing session,
    stack trace, breakpoints, etc. are reset).
    """

    impl = get_global_robot_debugger()

    if impl is None:
        # Note: only patches once, afterwards, returns the same instance.
        from robotframework_debug_adapter.listeners import DebugListener
        from robotframework_debug_adapter.listeners import DebugListenerV2

        impl = _RobotDebuggerImpl()

        DebugListener.on_start_suite.register(impl.start_suite)
        DebugListener.on_end_suite.register(impl.end_suite)

        DebugListener.on_start_test.register(impl.start_test)
        DebugListener.on_end_test.register(impl.end_test)

        DebugListener.on_log_message.register(impl.log_message)
        DebugListener.on_message.register(impl.message)

        # On RobotFramework 3.x and earlier 4.x dev versions, we do some monkey-patching because
        # the listener was not able to give linenumbers.
        from robot import get_version

        version = get_version()
        use_monkeypatching = version.startswith("3.") or version.startswith("4.0.a")

        if not use_monkeypatching:
            # 4.0.0 onwards
            DebugListenerV2.on_start_keyword.register(impl.start_keyword_v2)
            DebugListenerV2.on_end_keyword.register(impl.end_keyword_v2)
        else:
            # Older versions
            try:
                _apply_monkeypatching_before_4_b_2(impl)
            except ImportError:
                _apply_monkeypatching_latest(impl)

        set_global_robot_debugger(impl)
    else:
        impl.reset()

    return impl
