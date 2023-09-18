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
from __future__ import annotations
import json


from robocorp_ls_core.debug_adapter_core.dap import dap_base_schema as base_schema
from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import BaseSchema
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    Breakpoint,
    ConfigurationDoneRequest,
    ConfigurationDoneResponse,
    ContinueRequest,
    DisconnectRequest,
    EvaluateRequest,
    InitializeRequest,
    InitializedEvent,
    LaunchRequest,
    LaunchResponse,
    NextRequest,
    PauseRequest,
    ScopesRequest,
    SetBreakpointsRequest,
    SetBreakpointsResponseBody,
    SetExceptionBreakpointsRequest,
    SourceBreakpoint,
    StackTraceRequest,
    StepInRequest,
    StepOutRequest,
    ThreadsRequest,
    VariablesRequest,
)
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.constants import DEBUG
from typing import Optional


log = get_logger(__name__)


class DebugAdapterComm(object):
    """
    This is the class that actually processes commands from the client (VSCode)
    using the process stdin/stdout.

    It's responsible for actually starting the debugger process later on.

    It's created in the main thread and then control is passed on to the reader thread so that whenever
    something is read the json is handled by this processor.

    The queue it receives in the constructor should be used to talk to the writer thread, where it's expected
    to post protocol messages (which will be converted with 'to_dict()' and will have the 'seq' updated as
    needed).
    """

    def __init__(self, write_to_client_queue):
        from robotframework_debug_adapter.launch_process import LaunchProcess

        self.write_to_client_queue = write_to_client_queue
        self._launch_process: Optional[LaunchProcess] = None
        self._supports_run_in_terminal = False
        self._initialize_request_arguments = None
        self._run_in_debug_mode = True

        # i.e.: When a backend receives a stopped event, it sets itself as
        # a weakreference in weak_stopped_target_comm (so that we can redirect
        # related events, such as evaluate, stack trace, etc to the proper
        # backend).
        self.weak_stopped_target_comm = lambda: None

    @property
    def supports_run_in_terminal(self):
        return self._supports_run_in_terminal

    @property
    def initialize_request_arguments(self):
        return self._initialize_request_arguments

    def from_client(self, protocol_message):
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )

        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug("%s: READER_THREAD_STOPPED." % (self.__class__.__name__,))
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        if protocol_message.type == "request":
            method_name = "on_%s_request" % (protocol_message.command,)
            on_request = getattr(self, method_name, None)
            if on_request is not None:
                on_request(protocol_message)
            else:
                if DEBUG:
                    log.debug(
                        "Unhandled: %s not available in %s.\n"
                        % (method_name, self.__class__.__name__)
                    )

    def on_initialize_request(self, request: InitializeRequest):
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            InitializeResponse,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Capabilities

        self._initialize_request_arguments = request.arguments
        initialize_response: InitializeResponse = build_response(request)
        self._supports_run_in_terminal = request.arguments.supportsRunInTerminalRequest
        capabilities: Capabilities = initialize_response.body
        capabilities.supportsConfigurationDoneRequest = True
        capabilities.supportsConditionalBreakpoints = True
        capabilities.supportsEvaluateForHovers = True
        capabilities.supportsHitConditionalBreakpoints = True
        capabilities.supportsLogPoints = True
        capabilities.exceptionBreakpointFilters = [
            {"filter": "logFailure", "label": "Robot Log FAIL", "default": True},
            {"filter": "logError", "label": "Robot Log ERROR", "default": True},
        ]
        # capabilities.supportsSetVariable = True
        self.write_to_client_message(initialize_response)

    def on_launch_request(self, request: LaunchRequest):
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )
        from robotframework_debug_adapter.launch_process import LaunchProcess
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            SetDebuggerPropertyRequest,
            SetDebuggerPropertyArguments,
            AttachRequest,
            AttachRequestArguments,
        )

        self._run_in_debug_mode = run_in_debug_mode = not request.arguments.noDebug

        launch_response: LaunchResponse = build_response(request)
        launch_process = None
        try:
            self._launch_process = launch_process = LaunchProcess(
                request, launch_response, self
            )

            if launch_process.valid:
                # If on debug mode the launch is only considered finished when the connection
                # from the other side finishes properly.
                launch_process.launch()

                # Only write the initialized event after the process has been
                # launched so that we can forward breakpoints directly to the
                # target.
                self.write_to_client_message(InitializedEvent())
        except Exception as e:
            log.exception("Error launching.")
            launch_response.success = False
            launch_response.message = str(e)

        def on_finish_setup(*args, **kwargs):
            self.write_to_client_message(launch_response)  # acknowledge it
            if launch_process is not None:
                launch_process.after_launch_response_sent()

        if run_in_debug_mode and launch_process and launch_process.valid:
            # We must configure/attach to pydevd
            launch_process.write_to_pydevd(
                SetDebuggerPropertyRequest(
                    SetDebuggerPropertyArguments(
                        skipSuspendOnBreakpointException=("BaseException",),
                        skipPrintBreakpointException=("NameError",),
                        multiThreadsSingleNotification=True,
                    )
                )
            )

            attach_request_arguments = AttachRequestArguments(justMyCode=False)
            pydevd_attach_request = AttachRequest(attach_request_arguments)
            launch_process.write_to_pydevd(
                pydevd_attach_request, on_response=on_finish_setup
            )
        else:
            on_finish_setup()

    def on_configurationDone_request(self, request: ConfigurationDoneRequest):
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )

        configuration_done_response: ConfigurationDoneResponse = build_response(request)
        launch_process = self._launch_process
        if launch_process is None:
            configuration_done_response.success = False
            configuration_done_response.message = (
                "Launch is not done (configurationDone uncomplete)."
            )
            self.write_to_client_message(configuration_done_response)
            return

        if launch_process.send_and_wait_for_configuration_done_request():
            self.write_to_client_message(configuration_done_response)  # acknowledge it

        else:
            # timed out
            configuration_done_response.success = False
            configuration_done_response.message = (
                "Timed out waiting for configurationDone event."
            )
            self.write_to_client_message(configuration_done_response)

    def on_disconnect_request(self, request: DisconnectRequest):
        disconnect_response = base_schema.build_response(request)

        if self._launch_process is not None:
            self._launch_process.disconnect(request)

        self.write_to_client_message(disconnect_response)

    def on_pause_request(self, request: PauseRequest):
        if self._run_in_debug_mode and self._launch_process is not None:
            self._launch_process.resend_request_to_pydevd(request)
        else:
            pause_response = base_schema.build_response(request)
            self.write_to_client_message(pause_response)

    def on_evaluate_request(self, request: EvaluateRequest):
        if self._launch_process is not None:
            if request.arguments.context == "repl":
                pass
                # i.e.: if not stopped anywhere we could send to the stdin...
                # self._launch_process.send_to_stdin(request.arguments.expression)
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_setExceptionBreakpoints_request(
        self, request: SetExceptionBreakpointsRequest
    ):
        if self._run_in_debug_mode and self._launch_process is not None:
            self._launch_process.resend_request_to_robot(request)
        else:
            response = base_schema.build_response(request)
            self.write_to_client_message(response)

    def on_setBreakpoints_request(self, request: SetBreakpointsRequest):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            SetBreakpointsArguments,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Source

        if self._launch_process is None or not self._run_in_debug_mode:
            # Just acknowledge that no breakpoints are valid.
            breakpoints = []
            if request.arguments.breakpoints:
                for bp in request.arguments.breakpoints:
                    source_breakpoint = SourceBreakpoint(**bp)
                    breakpoints.append(
                        Breakpoint(
                            verified=False,
                            line=source_breakpoint.line,
                            source=request.arguments.source,
                        ).to_dict()
                    )

            self.write_to_client_message(
                base_schema.build_response(
                    request,
                    kwargs=dict(
                        body=SetBreakpointsResponseBody(breakpoints=breakpoints)
                    ),
                )
            )
            return

        arguments: SetBreakpointsArguments = request.arguments
        source: Source = arguments.source
        path = source.path
        if path and path.lower().endswith((".py", ".pyw")):
            self._launch_process.resend_request_to_pydevd(request)
        else:
            self._launch_process.resend_request_to_robot(request)

    def on_continue_request(self, request: ContinueRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_stepIn_request(self, request: StepInRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_stepOut_request(self, request: StepOutRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_stackTrace_request(self, request: StackTraceRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_next_request(self, request: NextRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_scopes_request(self, request: ScopesRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_variables_request(self, request: VariablesRequest):
        if self._launch_process:
            self._launch_process.resend_request_to_stopped_target(
                request, self.weak_stopped_target_comm()
            )

    def on_threads_request(self, request: ThreadsRequest):
        if self._launch_process:
            if self._run_in_debug_mode:
                self._launch_process.resend_request_to_pydevd(request)
            else:
                self._launch_process.resend_request_to_robot(request)

    def write_to_client_message(self, protocol_message: BaseSchema):
        """
        :param protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        self.write_to_client_queue.put(protocol_message)
