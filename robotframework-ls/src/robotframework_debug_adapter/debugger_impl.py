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
    REASON_BREAKPOINT,
    STEP_IN,
    REASON_STEP,
    STEP_NEXT,
)
import itertools
from functools import partial
from os.path import os
from robocode_ls_core.robotframework_log import get_logger
from collections import namedtuple
from robocode_ls_core.constants import IS_PY2


log = get_logger(__name__)


class RobotBreakpoint(object):
    def __init__(self, lineno):
        """
        :param int lineno:
            1-based line for the breakpoint.
        """
        self.lineno = lineno


class BusyWait(object):
    def __init__(self):
        self._event = threading.Event()
        self.before_wait = []

    def wait(self):
        for c in self.before_wait:
            c()
        self._event.wait()

    def proceed(self):
        self._event.set()
        self._event.clear()


class StackList(object):
    def __init__(self, frames):
        self.frames = frames


_StepEntry = namedtuple("_StepEntry", "ctx, step")


class _RobotDebuggerImpl(object):
    def __init__(self):
        from collections import deque

        self._filename_to_line_to_breakpoint = {}
        self.busy_wait = BusyWait()

        self._stack_list = None
        self._run_state = STATE_RUNNING
        self._step_cmd = None
        self._reason = None
        self._next_id = partial(next, itertools.count())
        self._ctx_deque = deque()
        self._step_next_stack_len = 0

    @property
    def stop_reason(self):
        return self._reason

    def get_stack_list(self):
        return self._stack_list

    def _create_stack_list(self, ctx, keyword):
        from robotframework_debug_adapter.dap import dap_schema

        ctx.namespace.get_library_instances()

        filename, _changed = file_utils.norm_file_to_client(keyword.source)
        name = os.path.basename(filename)

        frames = []
        for step_entry in self._ctx_deque:
            step = step_entry.step
            frames.append(
                dap_schema.StackFrame(
                    self._next_id(),
                    name=str(step),
                    line=step.lineno,
                    column=0,
                    source=dap_schema.Source(name=name, path=filename),
                )
            )

        stack_list = StackList(list(reversed(frames)))
        self._stack_list = stack_list

    def _dispose_stack_list(self):
        self._stack_list = None

    def wait_suspended(self, ctx, keyword, reason):
        log.info("wait_suspended", keyword, reason)
        self._create_stack_list(ctx, keyword)
        try:
            self._run_state = STATE_PAUSED
            self._reason = reason

            while self._run_state == STATE_PAUSED:
                self.busy_wait.wait()

            if self._step_cmd == STEP_NEXT:
                self._step_next_stack_len = len(self._ctx_deque)

        finally:
            self._dispose_stack_list()

    def step_continue(self):
        self._step_cmd = None
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    def step_in(self):
        self._step_cmd = STEP_IN
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    def step_next(self):
        self._step_cmd = STEP_NEXT
        self._run_state = STATE_RUNNING
        self.busy_wait.proceed()

    def set_breakpoints(self, filename, breakpoints):
        filename = file_utils.get_abs_path_real_path_and_base_from_file(filename)[0]
        line_to_bp = {}
        for bp in breakpoints:
            line_to_bp[bp.lineno] = bp
        self._filename_to_line_to_breakpoint[filename] = line_to_bp

    def before_run_step(self, step_runner, step):
        ctx = step_runner._context
        self._ctx_deque.append(_StepEntry(ctx, step))

        try:
            lineno = step.lineno
            source = step.source
            if IS_PY2 and isinstance(source, unicode):
                source = source.encode(file_utils.file_system_encoding)
        except AttributeError:
            return

        log.debug("run_step %s, %s - step: %s\n", step, lineno, self._step_cmd)
        source = file_utils.get_abs_path_real_path_and_base_from_file(source)[0]
        lines = self._filename_to_line_to_breakpoint.get(source)

        stop_reason = None
        step_cmd = self._step_cmd
        if lines and step.lineno in lines:
            stop_reason = REASON_BREAKPOINT

        elif step_cmd is not None:
            if step_cmd == STEP_IN:
                stop_reason = REASON_STEP

            elif step_cmd == STEP_NEXT:
                if len(self._ctx_deque) <= self._step_next_stack_len:
                    stop_reason = REASON_STEP

        if stop_reason is not None:
            ctx = step_runner._context
            self.wait_suspended(ctx, step, stop_reason)

    def after_run_step(self, step_runner, keyword):
        self._ctx_deque.pop()


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


def patch_execution_context():
    from robot.running.steprunner import StepRunner

    try:
        impl = patch_execution_context.impl
    except AttributeError:
        # Note: only patches once, afterwards, returns the same instance.

        impl = _RobotDebuggerImpl()
        _patch(StepRunner, impl, "run_step", impl.before_run_step, impl.after_run_step)
        patch_execution_context.impl = impl

    return patch_execution_context.impl
