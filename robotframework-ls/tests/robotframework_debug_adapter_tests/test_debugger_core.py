class DummyBusyWait(object):
    def __init__(self, debugger_impl):
        self.debugger_impl = debugger_impl
        self.waited = 0
        self.proceeded = 0
        self.stack = []
        self.on_wait = []

    def wait(self):
        self.waited += 1
        self.stack.append(self.debugger_impl.get_stack_list())
        action = self.on_wait.pop(0)
        action()

    def proceed(self):
        self.proceeded += 1


def test_debugger_core(debugger_api):
    import robot
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_impl.set_breakpoints(target, (RobotBreakpoint(4),))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_continue]

    code = robot.run_cli([target], exit=False)
    assert busy_wait.waited == 1
    assert busy_wait.proceeded == 1
    assert len(busy_wait.stack) == 1
    assert code == 0


def test_debugger_core_step_in(debugger_api):
    import robot
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_impl.set_breakpoints(target, (RobotBreakpoint(10),))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_in, debugger_impl.step_continue]

    code = robot.run_cli([target], exit=False)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0].frames] == ["My Equal Redefined"]
    assert [x.name for x in busy_wait.stack[1].frames] == [
        "Should Be Equal",
        "My Equal Redefined",
    ]
    assert code == 0


def test_debugger_core_step_next(debugger_api):
    import robot
    from robotframework_debug_adapter.debugger_impl import patch_execution_context
    from robotframework_debug_adapter.debugger_impl import RobotBreakpoint

    debugger_impl = patch_execution_context()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_impl.set_breakpoints(target, (RobotBreakpoint(10),))

    busy_wait = DummyBusyWait(debugger_impl)
    debugger_impl.busy_wait = busy_wait
    busy_wait.on_wait = [debugger_impl.step_next, debugger_impl.step_continue]

    code = robot.run_cli([target], exit=False)

    assert busy_wait.waited == 2
    assert busy_wait.proceeded == 2
    assert len(busy_wait.stack) == 2
    assert [x.name for x in busy_wait.stack[0].frames] == ["My Equal Redefined"]
    assert [x.name for x in busy_wait.stack[1].frames] == [
        "Yet Another Equal Redefined"
    ]
    assert code == 0
