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

        try:
            from robocorp_ls_core import uris

            target_robot = params.get("target_robot")
            log.debug("Selected robot:", target_robot)

            for ep in self._pm.get_implementations(EPResolveInterpreter):
                interpreter_info: IInterpreterInfo = (
                    ep.get_interpreter_info_for_doc_uri(
                        uris.from_fs_path(target_robot["filePath"])
                    )
                )
                if interpreter_info is not None:
                    from subprocess import check_output

                    python_path = interpreter_info.get_python_exe()
                    log.debug("Found python interpreter:", python_path)

                    # make sure we have the drivers installed
                    log.debug("Installing playwright drivers...")
                    cmd = [python_path, "-m", "playwright", "install"]
                    b_output = check_output(cmd, timeout=35)
                    output = b_output.decode("utf-8", "replace")

                    # open the playwright recorder
                    log.debug("Opening playwright recorder...")
                    cmd = [
                        python_path,
                        "-m",
                        "playwright",
                        "codegen",
                        "demo.playwright.dev/todomvc",
                    ]
                    b_output = check_output(cmd, timeout=35)
                    output += b_output.decode("utf-8", "replace")
                    log.debug("Recording ended successfully")

                    val = {
                        "success": True,
                        "message": None,
                        "result": output,
                    }
                    return val
        except Exception as e:
            log.error("Opening recorder failed:", e)
            return {
                "success": False,
                "message": "Running the Playwright Recorder failed. Please check environment for playwright package and try again."
                + str(e),
                "result": None,
            }

        # i.e.: no error but we couldn't find an interpreter.
        log.error("Could not resolve interpreter")
        return {
            "success": False,
            "message": "Could not resolve interpreter. Please check output logs.",
            "result": None,
        }
