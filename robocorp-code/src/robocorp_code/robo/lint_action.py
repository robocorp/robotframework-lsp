import json

from robocorp_ls_core.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
)
from robocorp_ls_core.pluginmanager import PluginManager
from robocorp_ls_core.protocols import IDocument
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.robo import lint_in_target_env

log = get_logger(__name__)


def collect_lint_errors(pm: PluginManager, doc: IDocument) -> list:
    """
    Note: the way this works is that we'll launch a separate script
    using the user environment to collect the linting information.

    The major reason this is done (vs just doing the linting in the
    current environment is that if we used the current environment,
    if the user uses a new version of python we could potentially
    have a syntax error (because for linting we need the python ast).
    """
    from robocorp_ls_core.basic import launch_and_return_future

    try:
        for ep in pm.get_implementations(EPResolveInterpreter):
            interpreter_info: IInterpreterInfo = ep.get_interpreter_info_for_doc_uri(
                doc.uri
            )
            if interpreter_info is not None:
                environ = interpreter_info.get_environ()
                python_exe = interpreter_info.get_python_exe()
                future = launch_and_return_future(
                    [python_exe, lint_in_target_env.__file__],
                    environ=environ,
                    cwd=None,
                    timeout=20,
                    stdin=doc.source.encode("utf-8", "replace"),
                )
                result = future.result(20)
                if result.returncode == 0:
                    if result.stdout:
                        try:
                            return json.loads(result.stdout)
                        except Exception:
                            log.exception(f"Unable to parse as json: {result.stdout}")

                if result.stderr:
                    log.info(
                        f"Found stderr while collecting lint errors: {result.stderr}"
                    )
    except BaseException:
        log.exception("Error collection @action")
    return []
