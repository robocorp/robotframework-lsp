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
import json
from robocorp_ls_core.debug_adapter_core.dap import dap_base_schema as base_schema
from robocorp_ls_core.robotframework_log import get_logger, get_log_level
from typing import Optional

log = get_logger(__name__)


class DebugAdapterComm(object):
    """
    This is the class that actually processes commands.

    It's created in the main thread and then control is passed on to the reader thread so that whenever
    something is read the json is handled by this processor.

    The queue it receives in the constructor should be used to talk to the writer thread, where it's expected
    to post protocol messages (which will be converted with 'to_dict()' and will have the 'seq' updated as
    needed).
    """

    def __init__(self, write_to_client_queue):
        self.write_to_client_queue = write_to_client_queue
        self._launch_process = None  # : :type self._launch_process: LaunchProcess
        self._supports_run_in_terminal = False
        self._initialize_request_arguments = None
        self._rcc_config_location: Optional[str] = None

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
            if get_log_level() > 1:
                log.debug("%s: READER_THREAD_STOPPED." % (self.__class__.__name__,))
            return

        if get_log_level() > 1:
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
                if get_log_level() > 1:
                    log.debug(
                        "Unhandled: %s not available in %s.\n"
                        % (method_name, self.__class__.__name__)
                    )

    def on_initialize_request(self, request):
        """
        :param InitializeRequest request:
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )

        # : :type initialize_response: InitializeResponse
        # : :type capabilities: Capabilities
        self._initialize_request_arguments = request.arguments
        initialize_response = build_response(request)
        self._supports_run_in_terminal = request.arguments.supportsRunInTerminalRequest
        self._rcc_config_location = request.arguments.kwargs.get("rccConfigLocation")
        capabilities = initialize_response.body
        capabilities.supportsConfigurationDoneRequest = True
        capabilities.supportsConditionalBreakpoints = True
        capabilities.supportsHitConditionalBreakpoints = True
        capabilities.supportsLogPoints = True
        # capabilities.supportsSetVariable = True
        self.write_to_client_message(initialize_response)

    def on_launch_request(self, request):
        """
        :param LaunchRequest request:
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import InitializedEvent
        from robocorp_code_debug_adapter.launch_process import LaunchProcess

        # : :type launch_response: LaunchResponse
        launch_response = build_response(request)
        launch_process = None
        try:

            self._launch_process = launch_process = LaunchProcess(
                request, launch_response, self, self._rcc_config_location
            )

            if launch_process.valid:
                self.write_to_client_message(InitializedEvent())

        except Exception as e:
            log.exception("Error launching.")
            launch_response.success = False
            launch_response.message = str(e)

        self.write_to_client_message(launch_response)  # acknowledge it

    def on_configurationDone_request(self, request):
        """
        Actually run when the configuration is finished.
        
        :param ConfigurationDoneRequest request:
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import (
            build_response,
        )

        configuration_done_response = build_response(request)
        launch_process = self._launch_process
        if launch_process is None:
            configuration_done_response.success = False
            configuration_done_response.message = (
                "Launch is not done (configurationDone uncomplete)."
            )
            self.write_to_client_message(configuration_done_response)
            return

        self.write_to_client_message(configuration_done_response)  # acknowledge it
        # Actually launch when the configuration is done.
        launch_process.launch()

    def on_disconnect_request(self, request):
        """
        :param DisconnectRequest request:
        """
        # : :type disconnect_response: DisconnectResponse
        disconnect_response = base_schema.build_response(request)

        if self._launch_process is not None:
            self._launch_process.disconnect(request)

        self.write_to_client_message(disconnect_response)

    def on_pause_request(self, request):
        """
        :param PauseRequest request:
        """
        # : :type pause_response: PauseResponse
        pause_response = base_schema.build_response(request)
        self.write_to_client_message(pause_response)

    def on_setExceptionBreakpoints_request(self, request):
        response = base_schema.build_response(request)
        self.write_to_client_message(response)

    def on_setBreakpoints_request(self, request):
        """
        :param SetBreakpointsRequest request:
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import SourceBreakpoint
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Breakpoint
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            SetBreakpointsResponseBody,
        )

        # Just acknowledge that no breakpoints are valid (we don't really debug,
        # we just run).
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
                kwargs=dict(body=SetBreakpointsResponseBody(breakpoints=breakpoints)),
            )
        )

    def on_threads_request(self, request):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Thread
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            ThreadsResponseBody,
        )

        threads = [Thread(0, "Main Thread").to_dict()]
        kwargs = {"body": ThreadsResponseBody(threads)}
        # : :type threads_response: ThreadsResponse
        threads_response = base_schema.build_response(request, kwargs)
        self.write_to_client_message(threads_response)

    def write_to_client_message(self, protocol_message):
        """
        :param BaseSchema protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        self.write_to_client_queue.put(protocol_message)
