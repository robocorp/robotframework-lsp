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

from functools import partial
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.constants import DEBUG
from robotframework_ls.options import DEFAULT_TIMEOUT
import itertools
import json
import os.path
import threading
import queue

log = get_logger(__name__)


class _DebugAdapterRobotTargetComm(threading.Thread):
    """
    This class is used so intermediate talking to the server.
    
    It's the middle ground between the `DebugAdapterComm` and `RobotTargetComm`.
        - `DebugAdapterComm`:
            It's used to talk with the client (in this process) and accessed
            through the _weak_debug_adapter_comm attribute.
             
        - `RobotTargetComm`
            It's actually in the target process. We communicate with it by 
            calling the `write_to_robot_message` method and receive messages
            from it in the `_from_robot` method in this class.
    """

    def __init__(self, debug_adapter_comm):
        threading.Thread.__init__(self)
        import weakref

        self._server_socket = None
        self._connected_event = threading.Event()

        self._process_event_msg = None
        self._process_event = threading.Event()

        self._terminated_event_msg = None
        self._terminated_event = threading.Event()

        self._write_to_robot_queue = queue.Queue()
        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)

        self._next_seq = partial(next, itertools.count(0))
        self._msg_id_to_on_response = {}

    def start_listening(self):
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.listen(1)
        self._server_socket = s
        self.start()
        return port

    def run(self):
        from robotframework_debug_adapter.debug_adapter_threads import (
            writer_thread_no_auto_seq,
        )
        from robotframework_debug_adapter.debug_adapter_threads import reader_thread

        try:
            assert (
                self._server_socket is not None
            ), "start_listening must be called before start()"

            # while True:
            # Only handle a single connection...
            socket, addr = self._server_socket.accept()

            read_from = socket.makefile("rb")
            write_to = socket.makefile("wb")

            debug_adapter_comm = self._weak_debug_adapter_comm()
            writer = self._writer_thread = threading.Thread(
                target=writer_thread_no_auto_seq,
                args=(write_to, self._write_to_robot_queue, "write to robot process"),
                name="Write to robot (_DebugAdapterRobotTargetComm)",
            )
            writer.daemon = True

            reader = self._reader_thread = threading.Thread(
                target=reader_thread,
                args=(
                    read_from,
                    self._from_robot,
                    debug_adapter_comm.write_to_client_queue,  # Used for errors
                    b"read from robot process",
                ),
                name="Read from robot (_DebugAdapterRobotTargetComm)",
            )
            reader.daemon = True

            reader.start()
            writer.start()

            self._connected_event.set()
        except:
            log.exception()

    def _from_robot(self, protocol_message):
        from robotframework_debug_adapter.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )

        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug(
                    "%s when reading from robot: READER_THREAD_STOPPED."
                    % (self.__class__.__name__,)
                )
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        try:
            on_response = None
            if protocol_message.type == "request":
                method_name = "on_%s_request" % (protocol_message.command,)
            elif protocol_message.type == "event":
                method_name = "on_%s_event" % (protocol_message.event,)
            elif protocol_message.type == "response":
                on_response = self._msg_id_to_on_response.pop(
                    protocol_message.request_seq, None
                )
                method_name = "on_%s_response" % (protocol_message.command,)
            else:
                if DEBUG:
                    log.debug(
                        "Unable to decide how to deal with protocol type: %s (read from robot - %s).\n"
                        % (protocol_message.type, self.__class__.__name__)
                    )
                return

            if on_response is not None:
                on_response(protocol_message)

            on_request = getattr(self, method_name, None)

            if on_request is not None:
                on_request(protocol_message)
            elif on_response is not None:
                pass
            else:
                if DEBUG:
                    log.debug(
                        "Unhandled: %s not available when reading from robot - %s.\n"
                        % (method_name, self.__class__.__name__)
                    )
        except:
            log.exception("Error")

    def on_process_event(self, event):
        self._process_event_msg = event
        self._process_event.set()

    def get_pid(self):
        assert self._process_event.is_set()
        return self._process_event_msg.body.systemProcessId

    def on_stopped_event(self, event):
        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    def on_terminated_event(self, event):
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEventBody

        self._terminated_event_msg = event
        self._terminated_event.set()
        self.write_to_robot_message(TerminatedEvent(TerminatedEventBody()))

    def write_to_robot_message(self, protocol_message, on_response=None):
        """
        :param BaseSchema protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        seq = protocol_message.seq = self._next_seq()
        if on_response is not None:
            self._msg_id_to_on_response[seq] = on_response
        self._write_to_robot_queue.put(protocol_message)

    def wait_for_connection(self):
        """
        :return bool:
            Returns True if the connection was successful and False otherwise.
        """
        assert self._server_socket is not None, "start_listening must be called first."
        log.debug("Wating for connection for %s seconds." % (DEFAULT_TIMEOUT,))
        ret = self._connected_event.wait(DEFAULT_TIMEOUT)
        log.debug("Connected: %s" % (ret,))
        return ret

    def wait_for_process_event(self):
        log.debug("Wating for process event for %s seconds." % (DEFAULT_TIMEOUT,))
        ret = self._process_event.wait(DEFAULT_TIMEOUT)
        log.debug("Received process event: %s" % (ret,))
        return ret

    def wait_for_process_terminated(self, timeout):
        return self._terminated_event.wait(timeout)


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

            time.sleep(0.5)
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
        "_launch_response",
        "_next_seq",
        "_track_process_pid",
        "_sent_terminated",
        "_env",
    ]

    def __init__(self, request, launch_response, debug_adapter_comm):
        """
        :param LaunchRequest request:
        :param LaunchResponse launch_response:
        """
        import weakref
        from robotframework_debug_adapter.constants import VALID_TERMINAL_OPTIONS
        from robotframework_debug_adapter.constants import TERMINAL_NONE
        from robocorp_ls_core.basic import as_str
        import robocorp_ls_core

        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)
        self._valid = True
        self._cmdline = []
        self._popen = None
        self._launch_response = launch_response
        self._next_seq = partial(next, itertools.count(0))
        self._track_process_pid = None
        self._sent_terminated = threading.Event()

        self._debug_adapter_robot_target_comm = _DebugAdapterRobotTargetComm(
            debug_adapter_comm
        )

        def mark_invalid(message):
            launch_response.success = False
            launch_response.message = message
            self._valid = False

        import sys

        target = request.arguments.kwargs.get("target")
        self._cwd = request.arguments.kwargs.get("cwd")
        self._terminal = request.arguments.kwargs.get("terminal", TERMINAL_NONE)
        args = request.arguments.kwargs.get("args") or []
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

        port = self._debug_adapter_robot_target_comm.start_listening()

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
                + [target]
            )

        self._cmdline = cmdline

    @property
    def valid(self):
        return self._valid

    @property
    def run_in_debug_mode(self):
        return self._run_in_debug_mode

    def notify_exit(self):
        if self._sent_terminated.is_set():
            return
        self._sent_terminated.set()
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEvent
        from robotframework_debug_adapter.dap.dap_schema import TerminatedEventBody

        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            restart = False
            terminated_event = TerminatedEvent(
                body=TerminatedEventBody(restart=restart)
            )
            debug_adapter_comm.write_to_client_message(terminated_event)

    def send_and_wait_for_configuration_done_request(self):
        from robotframework_debug_adapter.dap.dap_schema import ConfigurationDoneRequest
        from robotframework_debug_adapter.dap.dap_schema import (
            ConfigurationDoneArguments,
        )

        event = threading.Event()
        self._debug_adapter_robot_target_comm.write_to_robot_message(
            ConfigurationDoneRequest(ConfigurationDoneArguments()),
            on_response=lambda *args, **kwargs: event.set(),
        )
        log.debug(
            "Wating for configuration_done response for %s seconds."
            % (DEFAULT_TIMEOUT,)
        )
        ret = event.wait(DEFAULT_TIMEOUT)
        log.debug("Received configuration_done response: %s" % (ret,))
        return ret

    def resend_request_to_robot(self, request):
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

    def launch(self):
        from robotframework_debug_adapter.constants import TERMINAL_NONE
        from robotframework_debug_adapter.constants import TERMINAL_EXTERNAL
        from robotframework_debug_adapter.constants import TERMINAL_INTEGRATED
        from robotframework_debug_adapter.dap.dap_schema import RunInTerminalRequest
        from robotframework_debug_adapter.dap.dap_schema import (
            RunInTerminalRequestArguments,
        )
        from robotframework_debug_adapter.dap.dap_schema import OutputEvent
        from robotframework_debug_adapter.dap.dap_schema import OutputEventBody
        from robotframework_debug_adapter.dap.dap_schema import InitializeRequest
        from robotframework_debug_adapter.dap.dap_schema import (
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
            launch_response.message = "Debug adapter timed out waiting for connection."
            self._valid = False

        self._debug_adapter_robot_target_comm.write_to_robot_message(
            InitializeRequest(
                InitializeRequestArguments("robot-launch-process-adapter")
            )
        )
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

    def after_launch_response_sent(self):
        if self._track_process_pid is None:
            log.debug("Unable to track if pid is alive (pid unavailable).")
            return
        t = threading.Thread(
            target=_notify_on_exited_pid,
            args=(self.notify_exit, self._track_process_pid),
            name="Track PID alive",
        )
        t.daemon = True
        t.start()

    def disconnect(self, disconnect_request):
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
