import pytest  # type: ignore
import os
import threading
from robocorp_ls_core.options import DEFAULT_TIMEOUT
import sys
from robotframework_debug_adapter.dap.dap_schema import StackFrame
from typing import List, Optional, Dict, Callable, Iterable
from robotframework_debug_adapter.protocols import IBusyWait, IRobotDebugger
from robocorp_ls_core.basic import implements


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
        from robotframework_debug_adapter.constants import MAIN_THREAD_ID

        frames = self.debugger_impl.get_frames(MAIN_THREAD_ID)
        if not frames:
            self.stack.append([])
        else:
            self.stack.append(frames)
        action = self.on_wait.pop(0)
        action()

    @implements(IBusyWait.proceed)
    def proceed(self):
        self.proceeded += 1


class RunRobotThread(threading.Thread):
    def __init__(self, dap_logs_dir):
        threading.Thread.__init__(self)
        self.target = None
        self.dap_logs_dir = dap_logs_dir
        self.result_code = None
        self.result_event = threading.Event()

    def run(self):
        import robot  # type: ignore

        code = robot.run_cli(
            [
                "--outputdir=%s" % (self.dap_logs_dir,),
                "--listener=robotframework_debug_adapter.listeners.DebugListener",
                self.target,
            ],
            exit=False,
        )
        self.result_code = code

    def run_target(self, target):
        self.target = target
        self.start()


@pytest.fixture
def robot_thread(dap_logs_dir):
    """
    Fixture for interacting with the debugger api through a thread.
    """
    t = RunRobotThread(dap_logs_dir)
    yield t
    dbg_wait_for(
        lambda: t.result_code is not None,
        msg="Robot execution did not finish properly.",
    )


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
                target,
            ],
            exit=False,
        )
        return code

    yield run


def stack_frames_repr(
    stack_lst: Iterable[Optional[List[StackFrame]]]
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


def dbg_wait_for(condition, msg=None, timeout=DEFAULT_TIMEOUT, sleep=1 / 20.0):
    from robocorp_ls_core.basic import wait_for_condition

    if "pydevd" in sys.modules:
        timeout = sys.maxsize

    wait_for_condition(condition, msg, timeout, sleep)


def test_debugger_core(debugger_api_core, robot_thread) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    from robotframework_debug_adapter.constants import MAIN_THREAD_ID

    debugger_impl = install_robot_debugger()
    target = debugger_api_core.get_dap_case_file("case_log.robot")
    debugger_api_core.target = target
    line = debugger_api_core.get_line_index_with_content("check that log works")
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)
    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)

        stack = debugger_impl.get_frames(MAIN_THREAD_ID)
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 1)
    assert stack and len(stack) == 3
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_for(debugger_api, robot_thread, data_regression) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    from robotframework_debug_adapter.constants import MAIN_THREAD_ID

    debugger_impl = install_robot_debugger()
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    line = debugger_api.get_line_index_with_content("Break 1", target)
    debugger_impl.set_breakpoints(target, RobotBreakpoint(line))

    robot_thread.run_target(target)

    stack_lst: List[Optional[List[StackFrame]]] = []

    try:
        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 1)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 2)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 3)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        dbg_wait_for(lambda: debugger_impl.busy_wait.waited == 4)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 4)

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_keyword_if(debugger_api, robot_thread, data_regression) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    from robotframework_debug_adapter.constants import MAIN_THREAD_ID

    debugger_impl = install_robot_debugger()
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
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        check_waited(2)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        check_waited(3)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
        debugger_impl.step_in()

        check_waited(4)
        stack_lst.append(debugger_impl.get_frames(MAIN_THREAD_ID))
    finally:
        debugger_impl.step_continue()

    dbg_wait_for(lambda: debugger_impl.busy_wait.proceeded == 4)

    data_regression.check(stack_frames_repr(stack_lst))
    dbg_wait_for(lambda: robot_thread.result_code == 0)


def test_debugger_core_step_in(debugger_api, run_robot_cli) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = install_robot_debugger()
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


def test_debugger_core_step_next(debugger_api, run_robot_cli) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = install_robot_debugger()
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


def test_debugger_core_step_out(debugger_api, run_robot_cli) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = install_robot_debugger()
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
    debugger_api, run_robot_cli, data_regression
) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = install_robot_debugger()
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


def test_debugger_core_evaluate(debugger_api_core, robot_thread, tmpdir) -> None:
    from robotframework_debug_adapter.debugger_impl import install_robot_debugger
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    from robotframework_debug_adapter.constants import MAIN_THREAD_ID
    from robotframework_debug_adapter.debugger_impl import InvalidFrameIdError
    from robotframework_debug_adapter.debugger_impl import InvalidFrameTypeError

    debugger_impl = install_robot_debugger()
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
        frame_ids = list(debugger_impl.iter_frame_ids(MAIN_THREAD_ID))

        # Fail due to invalid frame id
        eval_info = debugger_impl.evaluate(
            invalid_frame_id, "Create File    %s    content=%s" % (filename, content)
        )
        with pytest.raises(InvalidFrameIdError):
            eval_info.future.result()

        # Fail because the stack selected is not a keyword stack.
        eval_info = debugger_impl.evaluate(
            frame_ids[-1], "Create File    %s    content=%s" % (filename, content)
        )
        with pytest.raises(InvalidFrameTypeError):
            eval_info.future.result()

        # Keyword evaluation works
        eval_info = debugger_impl.evaluate(
            frame_ids[0], "Create File    %s    content=%s" % (filename, content)
        )

        assert eval_info.future.result() is None
        with open(filename, "r") as stream:
            contents = stream.read()

        assert contents == content

        # Get variable in evaluation works
        eval_info = debugger_impl.evaluate(frame_ids[0], "${arg1}")
        assert eval_info.future.result() == "2"

        eval_info = debugger_impl.evaluate(frame_ids[0], "${ARG1}")
        assert eval_info.future.result() == "2"
    finally:
        debugger_impl.step_continue()
