from typing import List
from robocorp_code import commands
from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.protocols import ActionResultDict

log = get_logger(__name__)

playwright_command_dispatcher = _SubCommandDispatcher("_playwright")


class _Playwright(object):
    def __init__(
        self,
        base_command_dispatcher,
        feedback,
        plugin_manager,
    ):
        from robocorp_code._language_server_feedback import _Feedback

        self._feedback: _Feedback = feedback
        self._pm = plugin_manager

        base_command_dispatcher.register_sub_command_dispatcher(
            playwright_command_dispatcher
        )

    @playwright_command_dispatcher(
        commands.ROBOCORP_OPEN_PLAYWRIGHT_RECORDER_INTERNAL, dict
    )
    def _open_playwright_recorder(self, params=None) -> ActionResultDict:
        from robocorp_ls_core.ep_resolve_interpreter import EPResolveInterpreter
        from robocorp_ls_core.ep_resolve_interpreter import IInterpreterInfo
        from robocorp_ls_core import uris

        try:

            target_robot = params.get("target_robot")
            log.debug("Selected robot:", target_robot)

            for ep in self._pm.get_implementations(EPResolveInterpreter):
                interpreter_info: IInterpreterInfo = (
                    ep.get_interpreter_info_for_doc_uri(
                        uris.from_fs_path(target_robot["filePath"])
                    )
                )
                if interpreter_info is not None:
                    self.launch_playwright_recorder(interpreter_info.get_python_exe())
                    return ActionResultDict(
                        {
                            "success": True,
                            "message": None,
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

        # i.e.: no error but we couldn't find an interpreter.
        log.error("Could not resolve interpreter")
        return ActionResultDict(
            {
                "success": False,
                "message": "Could not resolve interpreter. Please check output logs.",
                "result": None,
            }
        )

    def launch_playwright_recorder(self, python_exe):
        import os
        import sys
        import threading
        import subprocess
        from robocorp_ls_core.basic import build_subprocess_kwargs

        cmd = [
            python_exe,
            os.path.join(os.path.dirname(__file__), "__playwright__main.py"),
        ]

        env = os.environ.copy()
        kwargs: dict = build_subprocess_kwargs(None, env, stderr=subprocess.PIPE)
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

        def on_output(content):
            try:
                sys.stderr.buffer.write(content)
            except:
                log.exception("Error reporting interactive output.")

        def stream_reader(stream, callback):
            try:
                for line in iter(stream.readline, b""):
                    callback(line)
            except Exception as e:
                log.error("Streaming failed:", e)

        process = subprocess.Popen(cmd, **kwargs)
        threads = [
            threading.Thread(
                target=stream_reader,
                args=(process.stdout, on_output),
                name="stream_reader_stdout",
            ),
            threading.Thread(
                target=stream_reader,
                args=(process.stderr, on_output),
                name="stream_reader_stderr",
            ),
        ]
        for t in threads:
            t.start()
