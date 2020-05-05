# Original work Copyright Fabio Zadrozny (EPL 1.0)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
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
import subprocess


def initialize(debugger_api):

    from robotframework_debug_adapter.dap.dap_schema import InitializeRequest
    from robotframework_debug_adapter.dap.dap_schema import InitializeRequestArguments
    from robotframework_debug_adapter.dap.dap_schema import InitializeResponse
    from robotframework_debug_adapter.dap.dap_schema import InitializedEvent

    debugger_api.write(
        InitializeRequest(
            InitializeRequestArguments(
                adapterID="robotframework-lsp-adapter",
                clientID="Stub",
                clientName="stub",
                locale="en-us",
                linesStartAt1=True,
                columnsStartAt1=True,
                pathFormat="path",
                supportsVariableType=True,
                supportsVariablePaging=True,
                supportsRunInTerminalRequest=True,
            )
        )
    )

    initialize_response = debugger_api.read(InitializeResponse)
    assert isinstance(initialize_response, InitializeResponse)
    assert initialize_response.request_seq == 0
    assert initialize_response.success
    assert initialize_response.command == "initialize"

    event = debugger_api.read(InitializedEvent)
    assert isinstance(event, InitializedEvent)


def launch(debugger_api, target, debug=True, success=True, terminal="none"):
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequest
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequestArguments
    from robotframework_debug_adapter.dap.dap_schema import LaunchResponse
    from robotframework_debug_adapter.dap.dap_schema import RunInTerminalRequest
    from robotframework_ls._utils import as_str
    import os

    debugger_api.write(
        LaunchRequest(
            LaunchRequestArguments(
                __sessionId="some_id",
                noDebug=not debug,
                target=target,
                terminal=terminal,
            )
        )
    )

    if terminal == "external":
        run_in_terminal_request = debugger_api.read(RunInTerminalRequest)
        env = os.environ.copy()
        for key, val in run_in_terminal_request.arguments.env.to_dict().items():
            env[as_str(key)] = as_str(val)
        subprocess.Popen(
            run_in_terminal_request.arguments.args,
            cwd=run_in_terminal_request.arguments.cwd,
            env=env,
        )

    launch_response = debugger_api.read(LaunchResponse)
    assert launch_response.success == success


def set_breakpoints(debugger_api, target, lines):
    import os.path
    from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsRequest
    from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsArguments
    from robotframework_debug_adapter.dap.dap_schema import Source
    from robotframework_debug_adapter.dap.dap_schema import SourceBreakpoint
    from robotframework_debug_adapter.dap.dap_schema import SetBreakpointsResponse

    assert isinstance(lines, (list, tuple))

    debugger_api.write(
        SetBreakpointsRequest(
            SetBreakpointsArguments(
                source=Source(name=os.path.basename(target), path=target),
                lines=lines,
                breakpoints=[SourceBreakpoint(line=line).to_dict() for line in lines],
            )
        )
    )
    response = debugger_api.read(SetBreakpointsResponse)
    assert len(response.body.breakpoints) == len(lines)


def test_invalid_launch_1(debugger_api):
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequest
    from robotframework_debug_adapter.dap.dap_schema import LaunchRequestArguments
    from robotframework_debug_adapter.dap.dap_schema import LaunchResponse

    initialize(debugger_api)

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


def test_invalid_launch(debugger_api):
    initialize(debugger_api)

    launch(debugger_api, "invalid_file.robot", debug=False, success=False)


def test_simple_launch(debugger_api):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent
    from robotframework_debug_adapter.dap.dap_schema import OutputEvent

    initialize(debugger_api)

    target = debugger_api.get_dap_case_file("case_log.robot")
    launch(debugger_api, target, debug=False)

    debugger_api.read(TerminatedEvent)
    debugger_api.assert_message_found(
        OutputEvent, lambda msg: "check that log works" in msg.body.output
    )


def test_launch_in_external_terminal(debugger_api):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent

    initialize(debugger_api)

    target = debugger_api.get_dap_case_file("case_log.robot")
    launch(debugger_api, target, debug=False, terminal="external")
    debugger_api.read(TerminatedEvent)


def finish_config(debugger_api):
    from robotframework_debug_adapter.dap.dap_schema import ConfigurationDoneRequest
    from robotframework_debug_adapter.dap.dap_schema import ConfigurationDoneResponse

    debugger_api.write(ConfigurationDoneRequest())
    debugger_api.read(ConfigurationDoneResponse)
