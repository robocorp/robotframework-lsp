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
import itertools
import os.path
import threading
from robocorp_ls_core.protocols import IConfig
from typing import Optional

log = get_logger(__name__)


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


class _DefaultConfigurationProvider(object):
    def __init__(self, config: IConfig):
        self.config = config


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
        "_rcc_config_location",
    ]

    def __init__(
        self,
        request,
        launch_response,
        debug_adapter_comm,
        rcc_config_location: Optional[str],
    ) -> None:
        """
        :param LaunchRequest request:
        :param LaunchResponse launch_response:
        """
        import weakref
        from robocorp_ls_core.basic import as_str
        from robocorp_code_debug_adapter.constants import VALID_TERMINAL_OPTIONS
        from robocorp_code_debug_adapter.constants import TERMINAL_NONE
        from robocorp_ls_core.robotframework_log import get_log_level
        from robocorp_code.rcc import Rcc
        from robocorp_ls_core.config import Config
        from pathlib import Path
        from robocorp_ls_core import yaml_wrapper
        from robocorp_ls_core.protocols import ActionResult
        from robocorp_code.protocols import IRobotYamlEnvInfo
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEventBody

        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)
        self._valid = True
        self._cmdline = []
        self._popen = None
        self._launch_response = launch_response
        self._next_seq = partial(next, itertools.count(0))
        self._track_process_pid = None
        self._sent_terminated = threading.Event()
        self._rcc_config_location = rcc_config_location

        def mark_invalid(message):
            launch_response.success = False
            launch_response.message = message
            self._valid = False

        robot_yaml = request.arguments.kwargs.get("robot")
        self._terminal = request.arguments.kwargs.get("terminal", TERMINAL_NONE)
        if self._terminal != TERMINAL_NONE:
            # We don't currently support the integrated terminal because we don't
            # have an easy way to get the launched process pid in this way.
            return mark_invalid(
                f"Only 'terminal=none' is supported. Found terminal: {self._terminal}"
            )

        task_name = request.arguments.kwargs.get("task", "")
        args = request.arguments.kwargs.get("args") or []
        if not isinstance(args, list):
            args = [args]
        args = [str(arg) for arg in args]

        env = {}
        request_env = request.arguments.kwargs.get("env")
        if isinstance(request_env, dict) and request_env:
            env.update(request_env)

        env = dict(((as_str(key), as_str(value)) for (key, value) in env.items()))

        self._env = env

        self._run_in_debug_mode = not request.arguments.noDebug

        if self._terminal not in VALID_TERMINAL_OPTIONS:
            return mark_invalid(
                "Invalid terminal option: %s (must be one of: %s)"
                % (self._terminal, VALID_TERMINAL_OPTIONS)
            )

        try:
            if robot_yaml is None:
                return mark_invalid("robot not provided in launch.")

            if not os.path.exists(robot_yaml):
                return mark_invalid("File: %s does not exist." % (robot_yaml,))
        except:
            log.exception("Error")
            return mark_invalid("Error checking if robot (%s) exists." % (robot_yaml,))

        self._cwd = os.path.dirname(robot_yaml)
        try:
            if self._cwd is not None:
                if not os.path.exists(self._cwd):
                    return mark_invalid(
                        "cwd specified does not exist: %s" % (self._cwd,)
                    )
        except:
            log.exception("Error")
            return mark_invalid("Error checking if cwd (%s) exists." % (self._cwd,))

        if get_log_level() > 1:
            log.debug("Run in debug mode: %s\n" % (self._run_in_debug_mode,))

        try:
            config = Config()
            config_provider = _DefaultConfigurationProvider(config)
            rcc = Rcc(config_provider=config_provider)
            rcc_executable = rcc.get_rcc_location()

            if not os.path.exists(rcc_executable):
                return mark_invalid(f"Expected: {rcc_executable} to exist.")
        except:
            log.exception("Error")
            return mark_invalid("Error getting rcc executable location.")

        else:
            task_args = []
            if task_name:
                task_args.append("--task")
                task_args.append(task_name)

            env_json_path = Path(robot_yaml).parent / "devdata" / "env.json"
            exists_env_json = env_json_path.exists()

            # Compute the space name
            try:
                with open(robot_yaml, "r") as stream:
                    yaml_contents = yaml_wrapper.load(stream)
            except:
                log.exception(f"Error loading {robot_yaml} as yaml.")
                return mark_invalid(f"Error loading {robot_yaml} as yaml.")

            if not isinstance(yaml_contents, dict):
                return mark_invalid(f"Expected dict as root in: {robot_yaml}.")

            conda_config = yaml_contents.get("condaConfigFile")
            if not conda_config:
                return mark_invalid(f"Could not find condaConfigFile in {robot_yaml}")
            parent: Path = Path(robot_yaml).parent
            conda_yaml_path = parent / conda_config
            if not conda_yaml_path.exists():
                return mark_invalid(f"conda.yaml does not exist in {conda_yaml_path}")

            try:
                conda_yaml_contents = conda_yaml_path.read_text("utf-8", "replace")
            except:
                log.exception(f"Error loading {conda_yaml_path} contents.")
                return mark_invalid(f"Error loading {conda_yaml_path} contents.")

            notify_event = threading.Event()

            import time

            def notify_elapsed_time():
                initial_time = time.time()

                notify_event.wait(5)
                if notify_event.is_set():
                    return

                output_event = OutputEvent(
                    OutputEventBody(
                        "Computing and creating environment (this can take some minutes)...\n",
                        category="stderr",
                    )
                )
                debug_adapter_comm.write_to_client_message(output_event)

                while True:
                    notify_event.wait(9.33)
                    elapsed = time.time() - initial_time
                    if not notify_event.is_set():
                        output_event = OutputEvent(
                            OutputEventBody(
                                "Elapsed: %.1fs\n" % (elapsed,), category="stderr"
                            )
                        )
                        debug_adapter_comm.write_to_client_message(output_event)

            t = threading.Thread(target=notify_elapsed_time)
            t.daemon = True
            t.start()

            try:
                robot_yaml_env_info: ActionResult[
                    IRobotYamlEnvInfo
                ] = rcc.get_robot_yaml_env_info(
                    Path(robot_yaml),
                    conda_yaml_path,
                    conda_yaml_contents,
                    env_json_path if exists_env_json else None,
                )
            finally:
                notify_event.set()

            if not robot_yaml_env_info.success:
                return mark_invalid(robot_yaml_env_info.message)
            robot_yaml_env_info_result: Optional[
                IRobotYamlEnvInfo
            ] = robot_yaml_env_info.result
            if not robot_yaml_env_info_result:
                return mark_invalid(
                    "Internal error: robot_yaml_env_info_result not available."
                )

            space_name = robot_yaml_env_info_result.space_info.space_name

            cmdline = (
                [
                    rcc_executable,
                    "task",
                    "run",
                    "--robot",
                    robot_yaml,
                    "--space",
                    space_name,
                ]
                + task_args
                + args
            )
            if self._rcc_config_location:
                cmdline.append("--config")
                cmdline.append(self._rcc_config_location)

            if exists_env_json:
                cmdline.append("-e")
                cmdline.append(str(env_json_path))

            cmdline.append("--controller")
            cmdline.append("RobocorpCode")

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
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            TerminatedEventBody,
        )

        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            restart = False
            terminated_event = TerminatedEvent(
                body=TerminatedEventBody(restart=restart)
            )
            debug_adapter_comm.write_to_client_message(terminated_event)

    def launch(self):
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            RunInTerminalRequest,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            RunInTerminalRequestArguments,
        )
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEvent
        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import OutputEventBody
        from robocorp_code_debug_adapter.constants import TERMINAL_NONE
        from robocorp_ls_core.robotframework_log import get_log_level
        from robocorp_code_debug_adapter.constants import TERMINAL_EXTERNAL
        from robocorp_code_debug_adapter.constants import TERMINAL_INTEGRATED

        # Note: using a weak-reference so that callbacks don't keep it alive
        weak_debug_adapter_comm = self._weak_debug_adapter_comm

        terminal = self._terminal
        if not weak_debug_adapter_comm().supports_run_in_terminal:
            # If the client doesn't support running in the terminal we fallback to using the debug console.
            terminal = TERMINAL_NONE

        threads = []
        if terminal == TERMINAL_NONE:
            import subprocess

            if get_log_level() > 1:
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

            self._track_process_pid = self._popen.pid

        elif terminal in (TERMINAL_INTEGRATED, TERMINAL_EXTERNAL):
            kind = terminal

            if get_log_level() > 1:
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
                # TODO: Get pid when running with terminal (get from response).

        if self._track_process_pid is None:
            log.debug("Unable to track if pid is alive (pid unavailable).")
        else:
            threads.append(
                threading.Thread(
                    target=_notify_on_exited_pid,
                    args=(self.notify_exit, self._track_process_pid),
                    name="Track PID alive",
                )
            )

        for t in threads:
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
