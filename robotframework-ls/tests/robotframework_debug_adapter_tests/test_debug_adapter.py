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

    debugger_api.wait_for_thread_stopped()

    debugger_api.continue_event()

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


def test_simple_debug_launch(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case_log.robot")

    debugger_api.launch(target, debug=True)
    threads_response = (
        debugger_api.list_threads()
    )  #: :type thread_response: ThreadsResponse
    assert len(threads_response.body.threads) == 1
    debugger_api.set_breakpoints(target, 4)
    debugger_api.configuration_done()

    debugger_api.wait_for_thread_stopped()

    debugger_api.continue_event()

    debugger_api.read(TerminatedEvent)


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

    debugger_api.continue_event()

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

    debugger_api.continue_event()

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

    debugger_api.continue_event()

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

    debugger_api.continue_event()

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

    debugger_api.continue_event()

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

    debugger_api.continue_event()

    json_hit = debugger_api.wait_for_thread_stopped(name="Should Be Equal")
    response = debugger_api.evaluate(
        "${arg1}", frameId=json_hit.frame_id, context="watch"
    )
    assert response.body.result in ("['2', '2']", "[u'2', u'2']")
    debugger_api.continue_event()

    debugger_api.read(TerminatedEvent)
