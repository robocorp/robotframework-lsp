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
import pytest
from robocorp_code_debug_adapter_tests.fixtures import _DebuggerAPI

from robocorp_code.rcc import Rcc


def test_invalid_launch_1(debugger_api: _DebuggerAPI, rcc_config_location: str):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        LaunchRequest,
        LaunchRequestArguments,
        Response,
    )

    debugger_api.initialize(rcc_config_location=rcc_config_location)

    debugger_api.write(
        LaunchRequest(
            LaunchRequestArguments(
                __sessionId="some_id",
                noDebug=True,
                # robot=robot, -- error: don't add robot
                terminal="none",
                cwd=None,
            )
        )
    )

    launch_response = debugger_api.read(Response)
    assert launch_response.success == False


def test_invalid_launch_2(debugger_api: _DebuggerAPI, rcc_config_location: str):
    debugger_api.initialize(rcc_config_location=rcc_config_location)

    debugger_api.launch("invalid_file.robot", "task1", debug=False, success=False)


def test_simple_launch(debugger_api: _DebuggerAPI, rcc: Rcc, rcc_config_location: str):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        OutputEvent,
        TerminatedEvent,
    )

    rcc.check_conda_installed()

    debugger_api.initialize(rcc_config_location=rcc_config_location)

    robot = debugger_api.get_dap_case_file("minimal/robot.yaml")
    debugger_api.launch(robot, "task1", debug=False)
    debugger_api.configuration_done()

    # i.e.: Big timeout because creating the environment may be slow.
    debugger_api.read(TerminatedEvent, timeout=360)
    debugger_api.assert_message_found(
        OutputEvent, lambda msg: "Task 1 executed" in msg.body.output
    )
    with pytest.raises(AssertionError):
        debugger_api.assert_message_found(
            OutputEvent, lambda msg: "Task 2 executed" in msg.body.output
        )


@pytest.mark.parametrize("override", [True, False])
def test_work_item_variables_not_overridden(
    debugger_api: _DebuggerAPI, rcc: Rcc, rcc_config_location: str, override: bool
):
    """
    Verifies that variables from env.json don't override variables related
    to work items set by Robocorp Code:
        - RPA_INPUT_WORKITEM_PATH
        - RPA_OUTPUT_WORKITEM_PATH
        - RPA_WORKITEMS_ADAPTER
    """
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        OutputEvent,
        TerminatedEvent,
    )

    rcc.check_conda_installed()

    debugger_api.initialize(rcc_config_location=rcc_config_location)

    robot = debugger_api.get_dap_case_file("project_with_env/robot.yaml")
    environ = {}
    if override:
        environ = {
            "RPA_INPUT_WORKITEM_PATH": "input workitem path",
            "RPA_OUTPUT_WORKITEM_PATH": "output workitem path",
            "RPA_WORKITEMS_ADAPTER": "workitems adapter",
        }
    debugger_api.launch(
        robot,
        "task1",
        debug=False,
        environ=environ,
    )
    debugger_api.configuration_done()

    # i.e.: Big timeout because creating the environment may be slow.
    debugger_api.read(TerminatedEvent, timeout=360)

    debugger_api.assert_message_found(
        OutputEvent,
        lambda msg: "SOME_OTHER_VAR: some other variable" in msg.body.output,
    )
    if override:
        with pytest.raises(AssertionError):
            # The environment variables from env.json were overridden and shouldn't be printed to stdout.
            debugger_api.assert_message_found(
                OutputEvent, lambda msg: "Will be ignored" in msg.body.output
            )

        for val in environ.values():
            debugger_api.assert_message_found(
                OutputEvent, lambda msg: val in msg.body.output
            )
    else:
        # Variables used will be the ones in env.json.
        debugger_api.assert_message_found(
            OutputEvent, lambda msg: "Will be ignored" in msg.body.output
        )


def not_supported_test_launch_in_external_terminal(
    debugger_api: _DebuggerAPI, rcc_config_location: str
):
    """
    This is an integrated test of the debug adapter. It communicates with it as if it was
    VSCode.

    Note: we don't currently support launching in an external terminal because there's
    no easy way to get the pid (it'd be possible to do that by creating a wrapper script
    which would then really launch rcc and then it'd connect back to some port and
    provide the pid of the process which was spawned, but the value gained vs the
    effort to do so seems low, which means we can only run without a terminal for
    now so that we have an easy way of tracking the RCC process pid).
    """
    import os

    from robocorp_ls_core.basic import as_str
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        RunInTerminalRequest,
        TerminatedEvent,
    )
    from robocorp_ls_core.subprocess_wrapper import subprocess

    debugger_api.initialize(rcc_config_location=rcc_config_location)

    robot = debugger_api.get_dap_case_file("minimal/robot.yaml")
    debugger_api.launch(robot, "task2", debug=False, terminal="external")
    debugger_api.configuration_done()

    run_in_terminal_request = debugger_api.read(RunInTerminalRequest)
    env = os.environ.copy()
    for key, val in run_in_terminal_request.arguments.env.to_dict().items():
        env[as_str(key)] = as_str(val)

    cwd = run_in_terminal_request.arguments.cwd
    popen_args = run_in_terminal_request.arguments.args

    subprocess.Popen(popen_args, cwd=cwd, env=env)

    # i.e.: Big timeout because creating the environment may be slow.
    debugger_api.read(TerminatedEvent, timeout=120)
