import os
from typing import List, Optional, Dict, Callable, Iterable

import pytest  # type: ignore

from robocorp_ls_core.basic import implements
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StackFrame
from robotframework_debug_adapter.protocols import IBusyWait, IRobotDebugger
from robotframework_debug_adapter_tests.fixtures import dbg_wait_for
from robotframework_ls.impl.robot_version import get_robot_major_version


# We don't even support version 2, so, this is ok.
IS_ROBOT_4_ONWARDS = get_robot_major_version() >= 4
IS_ROBOT_5_ONWARDS = get_robot_major_version() >= 5


class DummyBusyWait(object):
    def __init__(self, debugger_impl: IRobotDebugger):
        self.before_wait: List[Callable] = []
        self.debugger_impl = debugger_impl
        self.waited = 0
        self.proceeded = 0
        self.stack: List[List[StackFrame]] = []
        self.on_wait: List[Callable] = []

    @implements(IBusyWait.pre_wait)
    def pre_wait(self):
        for c in self.before_wait:
            c()

        self.waited += 1

    @implements(IBusyWait.wait)
    def wait(self) -> None:
        thread_id = self.debugger_impl.get_current_thread_id()
        frames = self.debugger_impl.get_frames(thread_id)
        if not frames:
            self.stack.append([])
        else:
            self.stack.append(frames)
        action = self.on_wait.pop(0)
        action()

    @implements(IBusyWait.proceed)
    def proceed(self):
        self.proceeded += 1


@pytest.fixture
def run_robot_cli(dap_logs_dir):
    """
    Fixture for interacting with the debugger api sequentially (in this same thread).
    """

    def run(target):
        import robot

        code = robot.run_cli(
            [
                "--outputdir=%s" % (dap_logs_dir,),
                "--listener=robotframework_debug_adapter.listeners.DebugListener",
                "--listener=robotframework_debug_adapter.listeners.DebugListenerV2",
                target,
            ],
            exit=False,
        )
        return code

    yield run


def stack_frames_repr(
    stack_lst: Iterable[Optional[List[StackFrame]]],
) -> Dict[str, List[str]]:
    dct = {}

    def to_dict(stack_frame):

        dct = stack_frame.to_dict()
        del dct["id"]
        path = dct["source"]["path"]
        if path != "None":
            if not os.path.exists(path):
                raise AssertionError("Expected: %r to exist." % (path,))
            # i.e.: make the path machine-independent
            dct["source"]["path"] = ".../" + os.path.basename(path)
        return dct

    for i, dap_frames in enumerate(stack_lst):
        if dap_frames is None:
            dct["Stack %s" % (i,)] = ["None"]
        else:
            dct["Stack %s" % (i,)] = [to_dict(x) for x in dap_frames]
    return dct


@pytest.fixture
def debugger_impl():
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger

    ret = install_robot_debugger()
    written = ret.written_messages = []

    def _write_message(msg):
        written.append(msg)

    ret.write_message = _write_message
    return ret


def test_debugger_core(debugger_api_core, robot_thread, debugger_impl) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api_core.get_dap_case_file("case_log.robot")
    debugger_api_core.target = target
    line = debugger_api_core.get_line_index_with_content("check that log works")
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)
    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

        stack = debugger_impl.get_frames(thread_id)
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 1)
    assert stack and len(stack) == 3
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_for(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 3)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 4)
        stack_lst.append(debugger_impl.get_frames(thread_id))

        n_proceeded = 4
        if IS_ROBOT_4_ONWARDS:
            # We have additional steps as we get one step with the creation
            # of the ${counter} variable when stepping into the for.
            debugger_impl.step_in()

            dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 5)
            stack_lst.append(debugger_impl.get_frames(thread_id))
            debugger_impl.step_in()

            dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 6)
            stack_lst.append(debugger_impl.get_frames(thread_id))
            n_proceeded = 6
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == n_proceeded)

    if IS_ROBOT_4_ONWARDS:
        basename = "test_debugger_core_for.v4"
    else:
        basename = "test_debugger_core_for.v3"
    data_regression.check(stack_frames_repr(stack_lst), basename=basename)
    dbg_wait_for(lambda: robot_thread.result_code == 0)


@pytest.mark.skipif(not IS_ROBOT_4_ONWARDS, reason="This is valid for RF4 onwards.")
def test_debugger_core_for_next(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 3)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 4)
        stack_lst.append(debugger_impl.get_frames(thread_id))

        # We have additional steps as we get one step with the creation
        # of the ${counter} variable when stepping into the for.
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 5)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 6)
        stack_lst.append(debugger_impl.get_frames(thread_id))
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 6)

    if IS_ROBOT_4_ONWARDS:
        basename = "test_debugger_core_for.v4"
    else:
        basename = "test_debugger_core_for.v3"
    data_regression.check(stack_frames_repr(stack_lst), basename=basename)
    dbg_wait_for(lambda: robot_thread.result_code == 0)


@pytest.mark.skipif(
    not IS_ROBOT_4_ONWARDS, reason="If statement only available in RF 4 onwards."
)
def test_debugger_core_if(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_if.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
        stack_lst.append(debugger_impl.get_frames(thread_id))
    finally:
        debugger_impl.step_in()  # Will actually finish the program now.

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 2)

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


@pytest.mark.skipif(
    not IS_ROBOT_4_ONWARDS, reason="If statement only available in RF 4 onwards."
)
def test_debugger_core_if_next(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_if.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_next()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
        stack_lst.append(debugger_impl.get_frames(thread_id))
    finally:
        debugger_impl.step_in()  # Will actually finish the program now.

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 2)

    data_regression.check(
        stack_frames_repr(stack_lst), basename="test_debugger_core_if"
    )
    dbg_wait_for(lambda: robot_thread.result_code == 0)


@pytest.mark.skipif(
    not IS_ROBOT_5_ONWARDS, reason="While statement only available in RF 5 onwards."
)
def test_debugger_core_while(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_while.robot"
    )
    line = debugger_api.get_line_index_with_content(
        "${SOMETHING}=    Evaluate    5", target
    )
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 3)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 4)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_continue()

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


@pytest.mark.skipif(
    not IS_ROBOT_5_ONWARDS, reason="Try statement only available in RF 5 onwards."
)
def test_debugger_core_try(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_try.robot"
    )
    line = debugger_api.get_line_index_with_content("Fail    Message", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    # stop on fail
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    # stop on except
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    # stop inside except
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 3)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    # stop on finally
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 4)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()

    # stop inside finally
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 5)
    stack_lst.append(debugger_impl.get_frames(thread_id))
    debugger_impl.step_next()  # Actually finishes it.

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_condition_breakpoint(
    debugger_api, robot_thread, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case_condition.robot")
    line = debugger_api.get_line_index_with_content("Log    ${counter}", target)

    debugger_impl.set_breakpoints(
        target, RobotBreakpoint(line, condition="${counter} == 2")
    )

    robot_thread.run_target(target)

    # It should only stop once (when counter == 2).
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    frame_ids = list(debugger_impl.iter_frame_ids(thread_id))
    eval_info = debugger_impl.evaluate(frame_ids[0], "${counter}")
    assert eval_info.future.result() == 2

    debugger_impl.step_continue()

    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_hit_condition_breakpoint(
    debugger_api, robot_thread, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case_condition.robot")
    line = debugger_api.get_line_index_with_content("Log    ${counter}", target)

    debugger_impl.set_breakpoints(target, RobotBreakpoint(line, hit_condition=2))

    robot_thread.run_target(target)

    # It should only stop once (when counter == 2).
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    frame_ids = list(debugger_impl.iter_frame_ids(thread_id))
    eval_info = debugger_impl.evaluate(frame_ids[0], "${counter}")
    assert eval_info.future.result() == 2

    debugger_impl.step_continue()

    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_keyword_if(
    debugger_api, robot_thread, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 2", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst = []

    def check_waited(expected):
        def msg():
            return "Expected waited to be: %s. Found: %s" % (
                expected,
                debugger_impl.busy_wait.waited,
            )

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == expected, msg=msg)

    try:
        check_waited(1)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        check_waited(2)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        check_waited(3)
        stack_lst.append(debugger_impl.get_frames(thread_id))
        debugger_impl.step_in()

        check_waited(4)
        stack_lst.append(debugger_impl.get_frames(thread_id))
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 4)

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_step_in(debugger_api, run_robot_cli, debugger_impl) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case4/case4.robot")
    line = debugger_api.get_line_index_with_content(
        "My Equal Redefined   2   2", target
    )
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_in, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0]] == [
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert [x.name for x in busy_wait.stack[1]] == [
        "Should Be Equal",
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert code == 0


def test_debugger_core_stop_on_failure_in_keyword(
    debugger_api, run_robot_cli, debugger_impl
) -> None:
    target = debugger_api.get_dap_case_file("case_failure.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 1
    assert len(busy_wait.stack) == 1
    assert [x.name for x in busy_wait.stack[0]] == [
        "Log (FAIL)",
        "This keyword does not exist",
        "TestCase: Check failure",
        "TestSuite: Case Failure",
    ]
    assert code != 0


def test_debugger_core_dont_stop_on_handled_failure_in_keyword(
    debugger_api, run_robot_cli, debugger_impl
) -> None:
    target = debugger_api.get_dap_case_file("case_failure_handled.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait

    code = run_robot_cli(target)

    assert busy_wait.waited == 0
    assert code == 0


@pytest.mark.skipif(not IS_ROBOT_5_ONWARDS, reason="This is valid for RF5 onwards.")
def test_debugger_core_dont_stop_on_handled_failure_in_except(
    debugger_api, run_robot_cli, debugger_impl
) -> None:
    target = debugger_api.get_dap_case_file("case_failure_handled_except.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait

    code = run_robot_cli(target)

    assert busy_wait.waited == 0
    assert code == 0


def test_debugger_core_stop_on_failure_in_import(
    debugger_api, run_robot_cli, debugger_impl
) -> None:
    target = debugger_api.get_dap_case_file("case_import_failure.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 1
    assert len(busy_wait.stack) == 1
    assert [x.name for x in busy_wait.stack[0]] == [
        "Log (ERROR)",
    ]
    # Note: Robot Framework considers it as passed even though there was an import error...
    assert code == 0


def test_debugger_core_stop_on_log_error_once(
    debugger_api, run_robot_cli, debugger_impl
) -> None:
    # Note: logging only happens in the main thread, so, we can't use
    # robot_thread.run_target(target)!

    target = debugger_api.get_dap_case_file("case_log_error.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 1
    assert len(busy_wait.stack) == 1
    assert [x.name for x in busy_wait.stack[0]] == [
        "Log (ERROR)",
        "Log",
        "TestCase: Check log",
        "TestSuite: Case Log Error",
    ]
    # Note: Robot Framework considers it as passed even though an error was logged...
    assert code == 0


def test_debugger_core_step_next(debugger_api, run_robot_cli, debugger_impl) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case4/case4.robot")
    line = debugger_api.get_line_index_with_content(
        "My Equal Redefined   2   2", target
    )
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_next, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0]] == [
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert [x.name for x in busy_wait.stack[1]] == [
        "Yet Another Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case4",
    ]
    assert code == 0


def test_debugger_core_step_out(debugger_api, run_robot_cli, debugger_impl) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case_step_out.robot")
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_out, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0]] == [
        "Should Be Equal",
        "My Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case Step Out",
    ]
    assert [x.name for x in busy_wait.stack[1]] == [
        "Yet Another Equal Redefined",
        "TestCase: Can use resource keywords",
        "TestSuite: Case Step Out",
    ]
    assert code == 0


def test_debugger_core_with_setup_teardown(
    debugger_api, run_robot_cli, data_regression, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    target = debugger_api.get_dap_case_file("case_setup_teardown.robot")
    debugger_impl.set_breakpoints(
        target,
        (
            RobotBreakpoint(
                debugger_api.get_line_index_with_content("Suite Setup", target)
            ),
            RobotBreakpoint(
                debugger_api.get_line_index_with_content("Suite Teardown", target)
            ),
        ),
    )

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue, debugger_impl.step_continue]

    code = run_robot_cli(target)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2

    data_regression.check(stack_frames_repr(busy_wait.stack))

    assert code == 0


def test_debugger_core_evaluate(
    debugger_api_core, robot_thread, tmpdir, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    from robotframework_debug_adapter.debugger_impl import InvalidFrameIdError
    from robotframework_debug_adapter.debugger_impl import InvalidFrameTypeError
    from robotframework_debug_adapter.debugger_impl import UnableToEvaluateError

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api_core.get_dap_case_file("case_evaluate.robot")
    debugger_api_core.target = target
    line = debugger_api_core.get_line_index_with_content("Break 1")
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

    try:
        invalid_frame_id = -11
        filename = str(tmpdir.join("file.txt"))
        filename = filename.replace("\\", "/")
        content = "file.txt"
        frame_ids = list(debugger_impl.iter_frame_ids(thread_id))

        # Fail due to invalid frame id
        eval_info = debugger_impl.evaluate(
            invalid_frame_id, "Create File    %s    content=%s" % (filename, content)
        )
        with pytest.raises(InvalidFrameIdError):
            eval_info.future.result()

        # Fail because the stack selected is not the top entry.
        eval_info = debugger_impl.evaluate(
            frame_ids[-1], "Create File    %s    content=%s" % (filename, content)
        )
        with pytest.raises(UnableToEvaluateError):
            eval_info.future.result()

        assert not os.path.exists(filename)

        # Keyword evaluation works
        eval_info = debugger_impl.evaluate(
            frame_ids[0], "Create File    %s    content=%s" % (filename, content)
        )

        assert eval_info.future.result() is None
        with open(filename, "r") as stream:
            contents = stream.read()

        assert contents == content

        # Get variable in evaluation works
        for context in ("watch", "hover", "repl"):
            eval_info = debugger_impl.evaluate(frame_ids[0], "${arg1}", context=context)
            assert eval_info.future.result() == "2"

            eval_info = debugger_impl.evaluate(frame_ids[0], "${ARG1}", context=context)
            assert eval_info.future.result() == "2"

        eval_info = debugger_impl.evaluate(
            frame_ids[0], "Should Be Equal", context="hover"
        )
        assert eval_info.future.result() == "BuiltIn.Should Be Equal"

    finally:
        debugger_impl.step_continue()


def test_debugger_core_evaluate_assign(
    debugger_api_core, robot_thread, debugger_impl
) -> None:
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    thread_id = debugger_impl.get_current_thread_id(robot_thread)
    target = debugger_api_core.get_dap_case_file("case_evaluate.robot")
    debugger_api_core.target = target
    line = debugger_api_core.get_line_index_with_content("Break 1")
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)
    dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

    try:
        frame_ids = list(debugger_impl.iter_frame_ids(thread_id))
        # Keyword evaluation works
        eval_info = debugger_impl.evaluate(
            frame_ids[0], "${lst}=    Create list    a    b"
        )

        assert eval_info.future.result() == ["a", "b"]
        # Get variable in evaluation works
        eval_info = debugger_impl.evaluate(frame_ids[0], "${lst}", context="repl")
        assert eval_info.future.result() == ["a", "b"]

    finally:
        debugger_impl.step_continue()


def test_debugger_core_evaluate_at_except_break(
    debugger_api, debugger_impl, run_robot_cli
) -> None:
    # Note: logging only happens in the main thread, so, we can't use
    # robot_thread.run_target(target)!
    target = debugger_api.get_dap_case_file("case_log_error.robot")

    debugger_impl.break_on_log_failure = True
    debugger_impl.break_on_log_error = True
    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait

    eval_info = None

    def on_wait_put_eval():
        nonlocal eval_info
        thread_id = debugger_impl.get_current_thread_id()
        frame_ids = list(debugger_impl.iter_frame_ids(thread_id))
        # Keyword evaluation works
        eval_info = debugger_impl.evaluate(
            frame_ids[0], "${lst}=    Create list    a    b"
        )

    def on_wait_evaluated():
        nonlocal eval_info
        assert eval_info.future.result() == ["a", "b"]
        debugger_impl.step_continue()

    busy_wait.on_wait = [on_wait_put_eval, on_wait_evaluated]

    code = run_robot_cli(target)

    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0]] == [
        "Log (ERROR)",
        "Log",
        "TestCase: Check log",
        "TestSuite: Case Log Error",
    ]
    # Note: Robot Framework considers it as passed even though an error was logged...
    assert code == 0
