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


def test_invalid_launch_1(debugger_api):
    """
    :param _DebuggerAPI debugger_api:
    """
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequest
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequestArguments
    from robotframework_debug_adapter.dap.dap_schema import LaunchResponse

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

    launch_response = debugger_api.read(LaunchResponse)
    assert launch_response.success == False


def test_invalid_launch_2(debugger_api):
    """
    :param _DebuggerAPI debugger_api:
    """

    debugger_api.initialize()

    debugger_api.launch("invalid_file.robot", debug=False, success=False)


def test_simple_launch(debugger_api):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    
    :param _DebuggerAPI debugger_api:
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent
    from robotframework_debug_adapter.dap.dap_schema import OutputEvent

    debugger_api.initialize()

    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_api.launch(target, debug=False)
    debugger_api.configuration_done()

    debugger_api.read(TerminatedEvent)
    debugger_api.assert_message_found(
        OutputEvent, lambda msg: "check that log works" in msg.body.output
    )


def test_simple_debug_launch(debugger_api):
    """
    :param _DebuggerAPI debugger_api:
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

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


def test_step_in(debugger_api):
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

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
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

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
    stack_frames = json_hit.stack_trace_response.body.stackFrames
    data_regression.check(
        format_stack_frames(stack_frames), basename="test_debugger_for_workflow_break"
    )

    debugger_api.step_in(json_hit.thread_id)
    json_hit = debugger_api.wait_for_thread_stopped("step")
    stack_frames = json_hit.stack_trace_response.body.stackFrames
    data_regression.check(
        format_stack_frames(stack_frames), basename="test_debugger_for_workflow_step_in"
    )

    debugger_api.continue_event()

    debugger_api.read(TerminatedEvent)


def test_step_next(debugger_api):
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

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


def test_variables(debugger_api):
    """
    :param _DebuggerAPI debugger_api:
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()
    target = debugger_api.get_dap_case_file("case4/case4.robot")
    debugger_api.target = target

    debugger_api.launch(target, debug=True)
    debugger_api.set_breakpoints(
        target, debugger_api.get_line_index_with_content("My Equal Redefined   2   2")
    )
    debugger_api.configuration_done()

    json_hit = debugger_api.wait_for_thread_stopped(name="My Equal Redefined")

    name_to_scope = debugger_api.get_name_to_scope(json_hit.frame_id)
    assert sorted(name_to_scope.keys()) == ["Arguments", "Variables"]
    name_to_var = debugger_api.get_arguments_name_to_var(json_hit.frame_id)
    assert sorted(name_to_var.keys()) == ["Arg 0", "Arg 1"]
    name_to_var = debugger_api.get_variables_name_to_var(json_hit.frame_id)
    assert "'${TEST_NAME}'" in name_to_var or "u'${TEST_NAME}'" in name_to_var
    assert "'${arg1}'" not in name_to_var and "u'${arg1}'" not in name_to_var

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


def test_launch_in_external_terminal(debugger_api):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    
    :param _DebuggerAPI debugger_api:
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

    debugger_api.initialize()

    target = debugger_api.get_dap_case_file("case_log.robot")
    debugger_api.launch(target, debug=False, terminal="external")
    debugger_api.configuration_done()
    debugger_api.read(TerminatedEvent)
