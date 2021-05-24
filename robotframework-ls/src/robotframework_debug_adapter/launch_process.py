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

from functools import partial
import itertools
import os.path
import threading
from typing import Optional
import typing

from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import BaseSchema
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    LaunchRequest,
    LaunchResponse,
    DisconnectRequest,
)
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.base_launch_process_target import (
    IProtocolMessageCallable,
)
from robotframework_debug_adapter.constants import DEBUG
from robotframework_ls.options import DEFAULT_TIMEOUT


if typing.TYPE_CHECKING:
    from robotframework_debug_adapter.debug_adapter_comm import DebugAdapterComm

log = get_logger(__name__)


def _noop(*args, **kwargs):
    pass


def _read_stream(stream, on_line, category):
    try:
        while True:
            output = stream.readline()
            if len(output) == 0:
                log.debug("Finished reading stream: %s.\n" % (category,))
                break
            output = output.decode("utf-8", errors="replace")
            on_line(output, category)
    except:
        log.exception("Error")


def _notify_on_exited_pid(on_exit, pid):
    try:
        from robocorp_ls_core.basic import is_process_alive
        import time

        log.debug("Waiting for pid to exit (_notify_on_exited_pid).")

        while True:
            if not is_process_alive(pid):
                break

            time.sleep(0.2)
        log.debug("pid exited (_notify_on_exited_pid).")
        on_exit()
    except:
        log.exception("Error")


class LaunchProcess(object):

    __slots__ = [
        "_valid",
        "_cmdline",
        "_terminal",
        "_popen",
        "_weak_debug_adapter_comm",
        "__weakref__",
        "_cwd",
        "_run_in_debug_mode",
        "_debug_adapter_robot_target_comm",
        "_debug_adapter_pydevd_target_comm",
        "_launch_response",
        "_next_seq",
        "_track_process_pid",
        "_env",
    ]

    def __init__(
        self,
        request: LaunchRequest,
        launch_response: LaunchResponse,
        debug_adapter_comm: DebugAdapterComm,
    ) -> None:
        self._init(request, launch_response, debug_adapter_comm)

    def _init(
        self,
        request: LaunchRequest,
        launch_response: LaunchResponse,
        debug_adapter_comm: DebugAdapterComm,
    ) -> None:
        import weakref
        from robotframework_debug_adapter.constants import VALID_TERMINAL_OPTIONS
        from robotframework_debug_adapter.constants import TERMINAL_NONE
        from robocorp_ls_core.basic import as_str
        import robocorp_ls_core
        from robotframework_debug_adapter.launch_process_robot_target_comm import (
            LaunchProcessDebugAdapterRobotTargetComm,
        )
        from robotframework_debug_adapter.launch_process_pydevd_comm import (
            LaunchProcessDebugAdapterPydevdComm,
        )

        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)
        self._valid = True
        self._cmdline = []
        self._popen = None
        self._launch_response = launch_response
        self._next_seq = partial(next, itertools.count(0))
        self._track_process_pid = None

        def mark_invalid(message):
            launch_response.success = False
            launch_response.message = message
            self._valid = False

        import sys

        target = request.arguments.kwargs.get("target")
        self._cwd = request.arguments.kwargs.get("cwd")
        self._terminal = request.arguments.kwargs.get("terminal", TERMINAL_NONE)
        args = request.arguments.kwargs.get("args") or []
        make_suite = request.arguments.kwargs.get("makeSuite", True)
        args = [str(arg) for arg in args]

        env = {}
        request_env = request.arguments.kwargs.get("env")
        if isinstance(request_env, dict) and request_env:
            env.update(request_env)

        pythonpath = env.get("PYTHONPATH", "")
        pythonpath += (
            os.pathsep
            + os.path.dirname(os.path.dirname(__file__))
            + os.pathsep
            + os.path.dirname(os.path.dirname(robocorp_ls_core.__file__))
        )
        env["PYTHONPATH"] = pythonpath

        for key, value in os.environ.items():
            if "ROBOTFRAMEWORK" in key:
                env[key] = value

        env = dict(((as_str(key), as_str(value)) for (key, value) in env.items()))

        self._env = env

        self._run_in_debug_mode = not request.arguments.noDebug

        if self._terminal not in VALID_TERMINAL_OPTIONS:
            return mark_invalid(
                "Invalid terminal option: %s (must be one of: %s)"
                % (self._terminal, VALID_TERMINAL_OPTIONS)
            )

        try:
            if self._cwd is not None:
                if not os.path.exists(self._cwd):
                    return mark_invalid(
                        "cwd specified does not exist: %s" % (self._cwd,)
                    )
        except:
            log.exception("Error")
            return mark_invalid("Error checking if cwd (%s) exists." % (self._cwd,))

        try:
            if target is None:
                return mark_invalid("target not provided in launch.")

            if not os.path.exists(target):
                return mark_invalid("File: %s does not exist." % (target,))
        except:
            log.exception("Error")
            return mark_invalid("Error checking if target (%s) exists." % (target,))

        if DEBUG:
            log.debug("Run in debug mode: %s\n" % (self._run_in_debug_mode,))

        self._debug_adapter_robot_target_comm = LaunchProcessDebugAdapterRobotTargetComm(
            debug_adapter_comm
        )

        port, server_socket = self._debug_adapter_robot_target_comm.start_listening(
            2 if self._run_in_debug_mode else 1
        )

        self._debug_adapter_pydevd_target_comm = LaunchProcessDebugAdapterPydevdComm(
            debug_adapter_comm, server_socket
        )

        try:
            run_robot_py = os.path.join(
                os.path.dirname(__file__), "run_robot__main__.py"
            )
            if not os.path.exists(run_robot_py):
                return mark_invalid("File: %s does not exist." % (run_robot_py,))
        except:
            log.exception("Error")
            return mark_invalid("Error checking if run_robot__main__.py exists.")

        else:
            target_args = [target]
            if make_suite:
                if os.path.isfile(target):
                    target_dir = os.path.dirname(target)
                    if os.path.exists(os.path.join(target_dir, "__init__.robot")):
                        target_name = os.path.splitext(os.path.basename(target))[0]
                        target_args = ["--suite", target_name, target_dir]

            # Note: target must be the last parameter.
            cmdline = (
                [
                    sys.executable,
                    "-u",
                    run_robot_py,
                    "--port",
                    str(port),
                    "--debug" if self._run_in_debug_mode else "--no-debug",
                ]
                + args
                + target_args
            )

        self._cmdline = cmdline

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def run_in_debug_mode(self) -> bool:
        return self._run_in_debug_mode

    def send_and_wait_for_configuration_done_request(self) -> bool:
        """
        :return: Whether the configuration done response was received.
        """
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            ConfigurationDoneRequest,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            ConfigurationDoneArguments,
        )

        event_robot = threading.Event()
        track_events = [event_robot]

        self._debug_adapter_robot_target_comm.write_to_robot_message(
            ConfigurationDoneRequest(ConfigurationDoneArguments()),
            on_response=lambda *args, **kwargs: event_robot.set(),
        )

        if self._run_in_debug_mode:
            event_pydevd = threading.Event()
            track_events.append(event_pydevd)
            self._debug_adapter_pydevd_target_comm.write_to_pydevd_message(
                ConfigurationDoneRequest(ConfigurationDoneArguments()),
                on_response=lambda *args, **kwargs: event_pydevd.set(),
            )

        log.debug(
            "Wating for configuration_done response for %s seconds."
            % (DEFAULT_TIMEOUT,)
        )
        ret = True
        for event in track_events:
            ret = ret and event.wait(DEFAULT_TIMEOUT)
            if not ret:
                break
        log.debug("Received configuration_done response: %s" % (ret,))
        return ret

    def resend_request_to_stopped_target(self, request: BaseSchema, target) -> None:
        if target is None:
            log.debug(f"Detected no paused backend to resend request: {request}")
            return

        if target is self._debug_adapter_pydevd_target_comm:
            self.resend_request_to_pydevd(request)
        elif target is self._debug_adapter_robot_target_comm:
            self.resend_request_to_robot(request)
        else:
            log.debug(
                f"Stopped target unexpected: {target} for resending request: {request}"
            )

    def resend_request_to_robot(self, request: BaseSchema) -> None:
        request_seq = request.seq

        def on_response(response_msg):
            response_msg.request_seq = request_seq
            debug_adapter_comm = self._weak_debug_adapter_comm()
            if debug_adapter_comm is not None:
                debug_adapter_comm.write_to_client_message(response_msg)
            else:
                log.debug(
                    "Command processor collected in resend request: %s" % (request,)
                )

        self._debug_adapter_robot_target_comm.write_to_robot_message(
            request, on_response
        )

    def resend_request_to_pydevd(self, request: BaseSchema) -> None:
        request_seq = request.seq

        def on_response(response_msg):
            response_msg.request_seq = request_seq
            debug_adapter_comm = self._weak_debug_adapter_comm()
            if debug_adapter_comm is not None:
                debug_adapter_comm.write_to_client_message(response_msg)
            else:
                log.debug(
                    "Command processor collected in resend request: %s" % (request,)
                )

        self._debug_adapter_pydevd_target_comm.write_to_pydevd_message(
            request, on_response
        )

    def write_to_robot_and_pydevd(self, request: BaseSchema):
        self._debug_adapter_robot_target_comm.write_to_robot_message(request)
        if self._run_in_debug_mode:
            self._debug_adapter_pydevd_target_comm.write_to_pydevd_message(request)

    def write_to_pydevd(
        self,
        request: BaseSchema,
        on_response: Optional[IProtocolMessageCallable] = None,
    ):
        if self._run_in_debug_mode:
            self._debug_adapter_pydevd_target_comm.write_to_pydevd_message(
                request, on_response=on_response
            )

    def launch(self):
        from robotframework_debug_adapter.constants import TERMINAL_NONE
        from robotframework_debug_adapter.constants import TERMINAL_EXTERNAL
        from robotframework_debug_adapter.constants import TERMINAL_INTEGRATED
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            RunInTerminalRequest,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            RunInTerminalRequestArguments,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEventBody
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import InitializeRequest
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            InitializeRequestArguments,
        )

        # Note: using a weak-reference so that callbacks don't keep it alive
        weak_debug_adapter_comm = self._weak_debug_adapter_comm

        terminal = self._terminal
        if not weak_debug_adapter_comm().supports_run_in_terminal:
            # If the client doesn't support running in the terminal we fallback to using the debug console.
            terminal = TERMINAL_NONE

        threads = []
        if terminal == TERMINAL_NONE:
            import subprocess

            if DEBUG:
                log.debug(
                    "Launching in debug console (not in terminal): %s"
                    % (self._cmdline,)
                )

            env = os.environ.copy()
            env.update(self._env)
            self._popen = subprocess.Popen(
                self._cmdline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                cwd=self._cwd,
                env=env,
            )

            def on_output(output, category):
                debug_adapter_comm = weak_debug_adapter_comm()
                if debug_adapter_comm is not None:
                    output_event = OutputEvent(
                        OutputEventBody(output, category=category)
                    )
                    debug_adapter_comm.write_to_client_message(output_event)

            stdout_stream_thread = threading.Thread(
                target=_read_stream,
                args=(self._popen.stdout, on_output, "stdout"),
                name="Read stdout",
            )
            stderr_stream_thread = threading.Thread(
                target=_read_stream,
                args=(self._popen.stderr, on_output, "stderr"),
                name="Read stderr",
            )

            threads.append(stdout_stream_thread)
            threads.append(stderr_stream_thread)

        elif terminal in (TERMINAL_INTEGRATED, TERMINAL_EXTERNAL):
            kind = terminal

            if DEBUG:
                log.debug('Launching in "%s" terminal: %s' % (kind, self._cmdline))

            debug_adapter_comm = weak_debug_adapter_comm()
            cmdline = self._cmdline
            if debug_adapter_comm is not None:
                debug_adapter_comm.write_to_client_message(
                    RunInTerminalRequest(
                        RunInTerminalRequestArguments(
                            cwd=self._cwd, args=cmdline, kind=kind, env=self._env
                        )
                    )
                )

        for t in threads:
            t.daemon = True

        if not self._debug_adapter_robot_target_comm.wait_for_connection():
            launch_response = self._launch_response
            launch_response.success = False
            launch_response.message = (
                "Debug adapter timed out waiting for Robot connection."
            )
            self._valid = False

        if self._run_in_debug_mode:
            # Ok, at this point we connected to the robot target debug adapter,
            # now, let's connect to pydevd too (if in debug mode).
            self._debug_adapter_pydevd_target_comm.start()
            if not self._debug_adapter_pydevd_target_comm.wait_for_connection():
                launch_response = self._launch_response
                launch_response.success = False
                launch_response.message = (
                    "Debug adapter timed out waiting for pydevd connection."
                )
                self._valid = False

        initialize_request = InitializeRequest(
            InitializeRequestArguments("robot-launch-process-adapter")
        )
        self.write_to_robot_and_pydevd(initialize_request)

        # Note: only start listening stdout/stderr when connected.
        for t in threads:
            t.start()

        if not self._debug_adapter_robot_target_comm.wait_for_process_event():
            launch_response = self._launch_response
            launch_response.success = False
            launch_response.message = (
                "Debug adapter timed out waiting for process event."
            )
            self._valid = False
        else:
            self._track_process_pid = self._debug_adapter_robot_target_comm.get_pid()

    def after_launch_response_sent(self) -> None:
        if self._track_process_pid is None:
            log.debug("Unable to track if pid is alive (pid unavailable).")
            return
        t = threading.Thread(
            target=_notify_on_exited_pid,
            args=(
                self._debug_adapter_robot_target_comm.notify_exit,
                self._track_process_pid,
            ),
            name="Track PID alive",
        )
        t.daemon = True
        t.start()

    def disconnect(self, disconnect_request: DisconnectRequest) -> None:
        from robocorp_ls_core.basic import kill_process_and_subprocesses

        if self._popen is not None:
            if self._popen.returncode is None:
                kill_process_and_subprocesses(self._popen.pid)
        else:
            kill_process_and_subprocesses(self._track_process_pid)

    def send_to_stdin(self, expression):
        popen = self._popen
        if popen is not None:
            try:
                log.debug("Sending: %s to stdin." % (expression,))

                def write_to_stdin(popen, expression):
                    popen.stdin.write(expression)
                    if not expression.endswith("\r") and not expression.endswith("\n"):
                        popen.stdin.write("\n")
                    popen.stdin.flush()

                # Do it in a thread (in theory the OS could have that filled up and we would never complete
                # trying to write -- although probably a bit far fetched, let's code as if that could actually happen).
                t = threading.Thread(
                    target=write_to_stdin,
                    args=(popen, expression),
                    name="Send to STDIN",
                )
                t.daemon = True
                t.start()
            except:
                log.exception("Error writing: >>%s<< to stdin." % (expression,))
