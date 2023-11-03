import errno
import os
from functools import partial
from typing import Dict, Union

from robocorp_ls_core import uris
from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code import commands
from robocorp_code.protocols import ActionResultDict

log = get_logger(__name__)

playwright_command_dispatcher = _SubCommandDispatcher("_playwright")


class _Playwright(object):
    def __init__(
        self, base_command_dispatcher, feedback, plugin_manager, lsp_messages
    ) -> None:
        from robocorp_ls_core.lsp import LSPMessages
        from robocorp_ls_core.pluginmanager import PluginManager

        from robocorp_code._language_server_feedback import _Feedback

        self._feedback: _Feedback = feedback
        self._pm: PluginManager = plugin_manager

        base_command_dispatcher.register_sub_command_dispatcher(
            playwright_command_dispatcher
        )
        self._lsp_messages: LSPMessages = lsp_messages

    @playwright_command_dispatcher(
        commands.ROBOCORP_OPEN_PLAYWRIGHT_RECORDER_INTERNAL,
        object,
    )
    def _open_playwright_recorder(
        self, params=None
    ) -> Union[ActionResultDict, partial]:
        target_robot_uri = params.get("target_robot_uri")
        if not target_robot_uri:
            return ActionResultDict(
                {
                    "success": False,
                    "message": "target_robot_uri must be passed.",
                    "result": None,
                }
            )
        log.debug("Selected robot:", target_robot_uri)
        return partial(
            self._threaded_playwright_recorder, target_robot_uri=target_robot_uri
        )

    def _threaded_playwright_recorder(self, target_robot_uri: str) -> ActionResultDict:
        from robocorp_ls_core.ep_resolve_interpreter import (
            EPResolveInterpreter,
            IInterpreterInfo,
        )

        try:
            for ep in self._pm.get_implementations(EPResolveInterpreter):
                interpreter_info: IInterpreterInfo = (
                    ep.get_interpreter_info_for_doc_uri(target_robot_uri)
                )
                if interpreter_info is not None:
                    path = uris.to_fs_path(target_robot_uri)
                    if os.path.isdir(path):
                        cwd = path
                    else:
                        cwd = os.path.dirname(path)
                        if not os.path.exists(cwd):
                            cwd = "."

                    environ = interpreter_info.get_environ()
                    if not environ:
                        # At this point the environ *must* be there.
                        return ActionResultDict(
                            {
                                "success": False,
                                "message": "Some internal error happened. The environ for the interpreter is empty.",
                                "result": None,
                            }
                        )
                    self._launch_playwright_recorder(
                        interpreter_info.get_python_exe(),
                        environ,
                        cwd=cwd,
                    )
                    return ActionResultDict(
                        {
                            "success": True,
                            "message": None,
                            "result": None,
                        }
                    )
            else:
                # i.e.: no error but we couldn't find an interpreter.
                log.error("Could not resolve interpreter")
                return ActionResultDict(
                    {
                        "success": False,
                        "message": "Could not resolve interpreter. Please check output logs.",
                        "result": None,
                    }
                )

        except Exception as e:
            log.error("Opening recorder failed:", e)
            return ActionResultDict(
                {
                    "success": False,
                    "message": "Running the Playwright Recorder failed. Please check environment for playwright package and try again."
                    + str(e),
                    "result": None,
                }
            )

    def _launch_playwright_recorder(
        self, python_exe: str, environ: Dict[str, str], cwd: str
    ) -> None:
        import subprocess
        import sys
        import threading

        from robocorp_ls_core.basic import build_subprocess_kwargs

        cmd = [
            python_exe,
            os.path.join(
                os.path.dirname(__file__), "playwright", "__playwright__main.py"
            ),
        ]

        full_env = dict(os.environ)
        full_env.update(environ)
        kwargs: dict = build_subprocess_kwargs(
            cwd,
            full_env,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        event = threading.Event()

        def stream_reader(stream):
            try:
                for line in iter(stream.readline, b""):
                    if not line:
                        break
                    if b"Playwright recorder started." in line:
                        event.set()
                    sys.stderr.buffer.write(line)
            except Exception as e:
                log.error("Error reading stream:", e)

        log.info(f'Running: {" ".join(str(x) for x in cmd)}')
        process = subprocess.Popen(cmd, **kwargs)

        # Not sure why, but (just when running in VSCode) something as:
        # launching sys.executable actually got stuck unless a \n was written
        # (even if stdin was closed it wasn't enough).
        # -- note: this may be particular to my machine (fabioz), but it
        # may also be related to VSCode + Windows 11 + Windows Defender + python
        _stdin_write(process, b"\n")

        threads = [
            threading.Thread(
                target=stream_reader,
                args=(process.stdout,),
                name="stream_reader_stdout",
            ),
            threading.Thread(
                target=stream_reader,
                args=(process.stderr,),
                name="stream_reader_stderr",
            ),
        ]
        for t in threads:
            t.start()

        def report_errors():
            from robocorp_ls_core.lsp import MessageType

            playwright_recorder_returncode = process.wait()
            # We didn't get the event saying that it started but the
            # process already finished.
            event.set()

            if playwright_recorder_returncode != 0:
                self._lsp_messages.show_message(
                    "There was some error running the Playwright recorder.\nPlease see `View > OUTPUT > Robocorp Code` for more details.",
                    MessageType.Error,
                )

        threading.Thread(target=report_errors).start()

        # Wait until we get a signal that the playwright recorder started
        # (or the timeout elapses -- ideally we should just leave this method when
        # the browser window is actually opened).

        timeout = 200
        # The timeout is big because if playwright needs to be installed it can take
        # quite a while.
        if not event.wait(timeout):
            if process.returncode is not None:
                log.info(
                    "Progress being hidden due to timeout (playwright recorder may not have started yet)."
                )


def _stdin_write(process, input):
    if input:
        try:
            process.stdin.write(input)
        except BrokenPipeError:
            pass  # communicate() must ignore broken pipe errors.
        except OSError as exc:
            if exc.errno == errno.EINVAL:
                # bpo-19612, bpo-30418: On Windows, stdin.write() fails
                # with EINVAL if the child process exited or if the child
                # process is still running but closed the pipe.
                pass
            else:
                raise

    try:
        process.stdin.close()
    except BrokenPipeError:
        pass  # communicate() must ignore broken pipe errors.
    except OSError as exc:
        if exc.errno == errno.EINVAL:
            pass
        else:
            raise
