# Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os.path
from robotframework_debug_adapter_tests.fixtures import _DebuggerAPI
import json
import pytest


def test_invalid_launch_1(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import LaunchRequest
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        LaunchRequestArguments,
    )
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Response

    debugger_api.initialize()

    debugger_api.write(
        LaunchRequest(
            LaunchRequestArguments(
                __sessionId="some_id",
                noDebug=True,
                # target=target, -- error: don't add target
                terminal="none",
                cwd=None,
            )
        )
    )

    launch_response = debugger_api.read(Response)
    assert launch_response.success == False


def test_invalid_launch_2(debugger_api: _DebuggerAPI):

    debugger_api.initialize()

    debugger_api.launch("invalid_file.robot", debug=False, success=False)


def test_error_handling(debugger_api: _DebuggerAPI):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Response
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Request

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_log.robot")

    debugger_api.launch(target, debug=True)

    # Let's write some invalid messages...
    debugger_api.write({})
    response = debugger_api.read(Response)
    assert not response.success

    debugger_api.write(Request("invalid_command"))
    response = debugger_api.read(Response)
    assert not response.success

    debugger_api.set_breakpoints(target, 4)
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped()

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_simple_launch(debugger_api: _DebuggerAPI):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent

    debugger_api.initialize()

    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_api.launch(target, debug=False)
    debugger_api.configuration_done()

    debugger_api.read(TerminatedEvent)
    debugger_api.assert_message_found(
        OutputEvent, lambda msg: "check that log works" in msg.body.output
    )


def test_log_message_in_console_output(debugger_api: _DebuggerAPI):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent

    debugger_api.initialize()

    target = debugger_api.get_dap_case_file("case_log_no_console.robot")
    debugger_api.launch(target, debug=True)
    debugger_api.configuration_done()

    debugger_api.read(TerminatedEvent)
    debugger_api.assert_message_found(
        OutputEvent, lambda msg: "LogNoConsole" in msg.body.output
    )


def test_simple_debug_launch_stop_on_robot(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import ThreadsResponse

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_log.robot")

    debugger_api.launch(target, debug=True)
    threads_response: ThreadsResponse = debugger_api.list_threads()
    assert len(threads_response.body.threads) == 1
    thread = next(iter(threads_response.body.threads))
    debugger_api.set_breakpoints(target, 4)
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="case_log.robot")
    assert json_hit.thread_id == thread["id"]

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_simple_debug_launch_stop_on_pydevd(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_python.robot")
    mypylib = debugger_api.get_dap_case_file("mypylib.py")

    debugger_api.launch(target, debug=True)
    threads_response = (
        debugger_api.list_threads()
    )  #: :type thread_response: ThreadsResponse
    assert len(threads_response.body.threads) == 1
    bp = debugger_api.get_line_index_with_content("break here", filename=mypylib)
    debugger_api.set_breakpoints(mypylib, bp)
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="mypylib.py")

    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)
    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_launch_pydevd_change_breakpoints(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_python.robot")
    mypylib = debugger_api.get_dap_case_file("mypylib.py")

    debugger_api.launch(target, debug=True)
    threads_response = (
        debugger_api.list_threads()
    )  #: :type thread_response: ThreadsResponse
    assert len(threads_response.body.threads) == 1
    bp1 = debugger_api.get_line_index_with_content("break on a = 1", filename=mypylib)
    bp2 = debugger_api.get_line_index_with_content("break on b = 2", filename=mypylib)
    debugger_api.set_breakpoints(mypylib, [bp1, bp2])
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="mypylib.py", line=bp1)
    debugger_api.set_breakpoints(mypylib, [])

    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)
    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_simple_debug_launch_stop_on_robot_and_pydevd(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import ThreadsResponse
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StoppedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import ContinuedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_python.robot")
    debugger_api.target = target
    mypylib = debugger_api.get_dap_case_file("mypylib.py")

    debugger_api.launch(target, debug=True)
    threads_response: ThreadsResponse = debugger_api.list_threads()
    assert len(threads_response.body.threads) == 1
    bp_robot = debugger_api.get_line_index_with_content("Some Call")
    bp_pydevd = debugger_api.get_line_index_with_content("break here", filename=mypylib)
    debugger_api.set_breakpoints(target, bp_robot)
    debugger_api.set_breakpoints(mypylib, bp_pydevd)
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="case_python.robot")

    # Note: because we're effectively dealing with 2 debuggers, it's possible that
    # the stopped event is received before the continued.
    msg = debugger_api.continue_event(
        json_hit.thread_id, additional_accepted=(StoppedEvent,)
    )
    if not isinstance(msg, StoppedEvent):
        debugger_api.wait_for_thread_stopped(file="mypylib.py")

    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)

    if not isinstance(msg, TerminatedEvent):
        # If we read Stopped before Continued, we may read a 2nd continued at this point.
        msg = debugger_api.read((TerminatedEvent, ContinuedEvent))

        if not isinstance(msg, TerminatedEvent):
            msg = debugger_api.read(TerminatedEvent)


def test_step_in(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("My Equal Redefined   2   2")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="My Equal Redefined")

    debugger_api.step_in(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped("step", name="Should Be Equal")

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def format_stack_frames(stack_frames):
    lst = []
    for stack_frame in stack_frames:
        dct = stack_frame.copy()
        del dct["id"]
        path = dct["source"]["path"]
        dct["source"]["path"] = os.path.basename(path)
        lst.append(dct)
    return lst


def test_debugger_for_workflow(debugger_api, data_regression):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robotframework_debug_adapter_tests.test_debugger_core import IS_ROBOT_4_ONWARDS

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("Break 1")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped()
    debugger_api.set_breakpoints(target, [])
    stack_frames = json_hit.stack_trace_response.body.stackFrames

    suffix = ".v3"
    if IS_ROBOT_4_ONWARDS:
        suffix = ".v4"

    data_regression.check(
        format_stack_frames(stack_frames),
        basename="test_debugger_for_workflow_break" + suffix,
    )

    debugger_api.step_in(json_hit.thread_id)
    json_hit = debugger_api.wait_for_thread_stopped("step")
    stack_frames = json_hit.stack_trace_response.body.stackFrames
    data_regression.check(
        format_stack_frames(stack_frames),
        basename="test_debugger_for_workflow_step_in" + suffix,
    )

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_step_next(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("My Equal Redefined   2   2")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="My Equal Redefined")

    debugger_api.step_next(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        "step", name="Yet Another Equal Redefined"
    )

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_invalid_launch_just_with_args_no_cwd(debugger_api: _DebuggerAPI):
    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target

    debugger_api.launch("<target-in-args>", args=[target], debug=True, success=False)


def test_launch_just_with_args(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target
    debugger_api.cwd = os.path.dirname(target)

    debugger_api.launch("<target-in-args>", args=[target], debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("My Equal Redefined   2   2")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="My Equal Redefined")

    debugger_api.step_next(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        "step", name="Yet Another Equal Redefined"
    )

    debugger_api.continue_event(json_hit.thread_id)
    debugger_api.read(TerminatedEvent)


def test_stop_on_condition(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_condition.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    line = debugger_api.get_line_index_with_content("Log    ${counter}")
    debugger_api.set_breakpoints(
        target, line, line_to_kwargs={line: {"condition": "${counter} == 2"}}
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="Log")

    name_to_scope = debugger_api.get_name_to_scope(json_hit.frame_id)
    assert sorted(name_to_scope.keys()) == ["Arguments", "Builtins", "Variables"]
    name_to_var = debugger_api.get_variables_name_to_var(json_hit.frame_id)
    assert name_to_var["'${counter}'"].value == "2"

    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)
    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_stop_on_hit_condition(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_condition.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    line = debugger_api.get_line_index_with_content("Log    ${counter}")
    debugger_api.set_breakpoints(
        target, line, line_to_kwargs={line: {"hitCondition": "2"}}
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="Log")

    name_to_scope = debugger_api.get_name_to_scope(json_hit.frame_id)
    assert sorted(name_to_scope.keys()) == ["Arguments", "Builtins", "Variables"]
    name_to_var = debugger_api.get_variables_name_to_var(json_hit.frame_id)
    assert name_to_var["'${counter}'"].value == "2"

    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)
    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_log_on_breakpoint(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_condition.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    line = debugger_api.get_line_index_with_content("Log    ${counter}")
    debugger_api.set_breakpoints(
        target, line, line_to_kwargs={line: {"logMessage": "Counter is: ${counter}"}}
    )
    debugger_api.configuration_done()
    debugger_api.read(TerminatedEvent)

    debugger_api.assert_message_found(
        OutputEvent,
        accept_msg=lambda output: output.body.output.strip() == "Counter is: 1",
    )
    debugger_api.assert_message_found(
        OutputEvent,
        accept_msg=lambda output: output.body.output.strip() == "Counter is: 2",
    )


def test_break_on_init(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target_folder = debugger_api.get_dap_case_file("check_init")
    target_init = debugger_api.get_dap_case_file("check_init/__init__.robot")
    debugger_api.target = target_folder

    debugger_api.launch(target_folder, debug=True)
    bp_setup = debugger_api.get_line_index_with_content(
        "Suite Setup", filename=target_init
    )
    bp_teardown = debugger_api.get_line_index_with_content(
        "Suite Teardown", filename=target_init
    )
    debugger_api.set_breakpoints(target_init, (bp_setup, bp_teardown))
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="__init__.robot")
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(file="__init__.robot")
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_init_auto_loaded(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("check_init/lsp_test.robot")
    target_init = debugger_api.get_dap_case_file("check_init/__init__.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    bp_setup = debugger_api.get_line_index_with_content(
        "Suite Setup", filename=target_init
    )
    bp_teardown = debugger_api.get_line_index_with_content(
        "Suite Teardown", filename=target_init
    )
    debugger_api.set_breakpoints(target_init, (bp_setup, bp_teardown))
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="check_init/__init__.robot")
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(file="check_init/__init__.robot")
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_sub_init_auto_loaded(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("check_sub_init/sub1/lsp_test.robot")
    target_init = debugger_api.get_dap_case_file("check_sub_init/__init__.robot")
    target_sub_init = debugger_api.get_dap_case_file(
        "check_sub_init/sub1/__init__.robot"
    )
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    for target in (target_init, target_sub_init):
        bp_setup = debugger_api.get_line_index_with_content(
            "Suite Setup", filename=target
        )
        bp_teardown = debugger_api.get_line_index_with_content(
            "Suite Teardown", filename=target
        )
        debugger_api.set_breakpoints(target, (bp_setup, bp_teardown))

    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init/sub1/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init/sub1/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_suite_with_prefix(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file(
        "check_suite_with_prefix/03__config/my.robot"
    )
    target_init = debugger_api.get_dap_case_file(
        "check_suite_with_prefix/03__config/__init__.robot"
    )
    debugger_api.target = target

    debugger_api.launch(target, debug=True)

    # Set init breaks
    bp_setup = debugger_api.get_line_index_with_content(
        "Suite Setup", filename=target_init
    )
    bp_teardown = debugger_api.get_line_index_with_content(
        "Suite Teardown", filename=target_init
    )
    debugger_api.set_breakpoints(target_init, (bp_setup, bp_teardown))
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_suite_with_prefix/03__config/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_suite_with_prefix/03__config/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


@pytest.mark.parametrize("scenario", ["cwd", "suite_target"])
def test_sub_init_auto_loaded_not_complete(debugger_api: _DebuggerAPI, scenario):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("check_sub_init2/sub1/sub2/lsp_test.robot")
    should_skip = debugger_api.get_dap_case_file("check_sub_init2/sub1/my.robot")
    target_init = debugger_api.get_dap_case_file("check_sub_init2/__init__.robot")

    debugger_api.target = target
    if scenario == "cwd":
        debugger_api.cwd = debugger_api.get_dap_case_file("check_sub_init2")
    else:
        debugger_api.cwd = debugger_api.get_dap_case_file("check_sub_init2/sub1/sub2")
        debugger_api.suite_target = debugger_api.get_dap_case_file("check_sub_init2")

    debugger_api.launch(target, debug=True)
    bp_setup = debugger_api.get_line_index_with_content(
        "Suite Setup", filename=target_init
    )
    bp_teardown = debugger_api.get_line_index_with_content(
        "Suite Teardown", filename=target_init
    )
    debugger_api.set_breakpoints(target_init, (bp_setup, bp_teardown))

    bp_to_skip = debugger_api.get_line_index_with_content(
        "This should not run", filename=should_skip
    )
    debugger_api.set_breakpoints(should_skip, bp_to_skip)

    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init2/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        file="check_sub_init2/__init__.robot"
    )
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_step_out(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_step_out.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("Break 1")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="Should Be Equal")

    debugger_api.step_out(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(
        "step", name="Yet Another Equal Redefined"
    )

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_failure(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import InitializeResponse

    initialize_response: InitializeResponse = debugger_api.initialize()
    assert initialize_response.body.exceptionBreakpointFilters == [
        {"filter": "logFailure", "label": "Robot Log FAIL", "default": True},
        {"filter": "logError", "label": "Robot Log ERROR", "default": True},
    ]
    target = debugger_api.get_dap_case_file("case_failure.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_exception_breakpoints(["logFailure", "logError"])
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(
        name="Log (FAIL)", reason="exception"
    )

    assert ([x["name"] for x in json_hit.stack_trace_response.body.stackFrames]) == [
        "Log (FAIL)",
        "This keyword does not exist",
        "TestCase: Check failure",
        "TestSuite: Case Failure",
    ]
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_import_failure(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import InitializeResponse

    initialize_response: InitializeResponse = debugger_api.initialize()
    assert initialize_response.body.exceptionBreakpointFilters == [
        {"filter": "logFailure", "label": "Robot Log FAIL", "default": True},
        {"filter": "logError", "label": "Robot Log ERROR", "default": True},
    ]
    target = debugger_api.get_dap_case_file("case_import_failure.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_exception_breakpoints(["logFailure", "logError"])
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(
        name="Log (ERROR)", reason="exception", file="case_import_failure.robot"
    )

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_variables(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True, args=["--variable", "my_var:22"])
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("My Equal Redefined   2   2")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="My Equal Redefined")

    name_to_scope = debugger_api.get_name_to_scope(json_hit.frame_id)
    assert sorted(name_to_scope.keys()) == ["Arguments", "Builtins", "Variables"]
    name_to_var = debugger_api.get_arguments_name_to_var(json_hit.frame_id)
    assert sorted(name_to_var.keys()) == ["Arg 0", "Arg 1"]
    name_to_var = debugger_api.get_variables_name_to_var(json_hit.frame_id)
    assert "'${TEST_NAME}'" not in name_to_var
    assert "'${arg1}'" not in name_to_var
    assert "'${my_var}'" in name_to_var

    name_to_var = debugger_api.get_builtins_name_to_var(json_hit.frame_id)
    assert "'${TEST_NAME}'" in name_to_var
    assert "'${arg1}'" not in name_to_var
    assert "'${my_var}'" not in name_to_var

    debugger_api.step_in(json_hit.thread_id)

    # Check that the 'arg1' var is in the current namespace but not in the parent
    # namespace.
    json_hit = debugger_api.wait_for_thread_stopped("step", name="Should Be Equal")
    name_to_var = debugger_api.get_variables_name_to_var(json_hit.frame_id)
    assert "'${arg1}'" in name_to_var or "u'${arg1}'" in name_to_var
    name_to_var = debugger_api.get_variables_name_to_var(
        json_hit.stack_trace_response.body.stackFrames[1]["id"]
    )
    assert "'${arg1}'" not in name_to_var and "u'${arg1}'" not in name_to_var

    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_launch_in_external_terminal(debugger_api: _DebuggerAPI):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()

    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_api.launch(target, debug=False, terminal="external")
    debugger_api.configuration_done()
    debugger_api.read(TerminatedEvent)


def test_evaluate(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_evaluate.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("Break 1")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="Should Be Equal")

    response = debugger_api.evaluate(
        "${arg1}", frameId=json_hit.frame_id, context="watch"
    )
    assert response.body.result == "2"

    response = debugger_api.evaluate(
        "My Equal Redefined     2   2", frameId=json_hit.frame_id, context="repl"
    )
    assert response.body.result == "None"

    assert json_hit.stack_trace_response.body.stackFrames[0]["id"] == json_hit.frame_id

    response = debugger_api.evaluate(
        "My Equal Redefined     2   1",
        frameId=json_hit.frame_id,
        context="repl",
        success=False,
    )
    assert "UserKeywordExecutionFailed: 2 != 1" in response.message

    # We can't evaluate keywords that are not in the top level.
    parent_frame_id = json_hit.stack_trace_response.body.stackFrames[1]["id"]
    response = debugger_api.evaluate(
        "My Equal Redefined     2   2",
        frameId=parent_frame_id,
        context="repl",
        success=False,
    )
    assert (
        "Keyword calls may only be evaluated at the topmost frame" in response.message
    )

    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("Break 2")
    )

    debugger_api.continue_event(json_hit.thread_id)

    json_hit = debugger_api.wait_for_thread_stopped(name="Should Be Equal")
    response = debugger_api.evaluate(
        "${arg1}", frameId=json_hit.frame_id, context="watch"
    )
    assert response.body.result in ("['2', '2']", "[u'2', u'2']")
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_evaluate_assign(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_evaluate.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("Break 1")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="Should Be Equal")

    response = debugger_api.evaluate(
        "${lst}=    Create list    a    b",
        frameId=json_hit.frame_id,
        context="repl",
    )
    assert response.body.result == "['a', 'b']"

    response = debugger_api.evaluate(
        "${lst}", frameId=json_hit.frame_id, context="watch"
    )
    assert response.body.result == "['a', 'b']"
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.read(TerminatedEvent)


def test_launch_multiple(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import ThreadsResponse

    debugger_api.initialize()
    target1 = debugger_api.get_dap_case_file("case_log.robot")
    target2 = debugger_api.get_dap_case_file("case_evaluate.robot")
    targets = [target1, target2]

    debugger_api.launch(targets, debug=True)
    threads_response: ThreadsResponse = debugger_api.list_threads()
    assert len(threads_response.body.threads) == 1

    bp1 = debugger_api.get_line_index_with_content("check that log works", target1)
    debugger_api.set_breakpoints(target1, bp1)

    bp2 = debugger_api.get_line_index_with_content("Break 1", target2)
    debugger_api.set_breakpoints(target2, bp2)

    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="case_log.robot")
    debugger_api.continue_event(json_hit.thread_id)

    debugger_api.wait_for_thread_stopped(file="case_evaluate.robot")
    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)

    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_launch_ignoring_tests(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target1 = debugger_api.get_dap_case_file("case_log.robot")
    target2 = debugger_api.get_dap_case_file("case_evaluate.robot")
    target3 = debugger_api.get_dap_case_file(
        "case_control_flow/case_control_flow_for.robot"
    )
    targets = [target1, target2, target3]

    debugger_api.launch(
        targets,
        debug=True,
        env={
            "RFLS_PRERUN_FILTER_TESTS": json.dumps(
                {"include": [[target1, "Check log"]], "exclude": []}
            )
        },
    )

    bp1 = debugger_api.get_line_index_with_content("check that log works", target1)
    debugger_api.set_breakpoints(target1, bp1)

    bp2 = debugger_api.get_line_index_with_content("Break 1", target2)
    debugger_api.set_breakpoints(target2, bp2)

    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="case_log.robot")
    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)

    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_launch_unicode(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("àèìòù.robot")

    debugger_api.launch(
        target,
        debug=True,
        env={
            "RFLS_PRERUN_FILTER_TESTS": json.dumps(
                {"include": [[target, "àèìòù"]], "exclude": []}
            )
        },
    )

    bp1 = debugger_api.get_line_index_with_content("Log to console    àèìòù", target)
    debugger_api.set_breakpoints(target, bp1)

    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(file="àèìòù.robot")
    msg = debugger_api.continue_event(json_hit.thread_id, accept_terminated=True)

    if not isinstance(msg, TerminatedEvent):
        debugger_api.read(TerminatedEvent)


def test_failure_message_from_library(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import InitializeResponse

    initialize_response: InitializeResponse = debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_fail_in_library/fail_at_robot.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.configuration_done()

    debugger_api.read(TerminatedEvent)
