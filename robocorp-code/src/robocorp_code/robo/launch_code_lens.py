import re
from functools import partial
from typing import List, Optional

from robocorp_ls_core.jsonrpc.endpoint import require_monitor
from robocorp_ls_core.lsp import CodeLensTypedDict
from robocorp_ls_core.protocols import (
    IConfig,
    IConfigProvider,
    IDocument,
    IMonitor,
    IWorkspace,
)


def compute_launch_robo_code_lens(
    workspace: Optional[IWorkspace], config_provider: IConfigProvider, doc_uri: str
) -> Optional[partial]:
    from robocorp_ls_core import uris

    if not uris.to_fs_path(doc_uri).endswith(".py"):
        return None
    ws = workspace
    if ws is None:
        return None

    config_provider = config_provider
    config: Optional[IConfig] = None
    compute_launch = True
    if config_provider is not None:
        config = config_provider.config
        if config:
            from robocorp_code.settings import ROBOCORP_CODE_LENS_ROBO_LAUNCH

            compute_launch = config.get_setting(
                ROBOCORP_CODE_LENS_ROBO_LAUNCH, bool, True
            )

    if not compute_launch:
        return None

    document: Optional[IDocument] = ws.get_document(doc_uri, accept_from_file=True)
    if document is None:
        return None

    # Provide a partial which will be computed in a thread with a monitor.
    return require_monitor(partial(_collect_tasks_in_thread, document))


def _collect_tasks_in_thread(
    document: IDocument, monitor: IMonitor
) -> Optional[List[CodeLensTypedDict]]:
    code_lenses: List[CodeLensTypedDict] = []
    contents = document.source
    found_task_decorator_at_line = -1

    for i, line in enumerate(contents.splitlines()):
        monitor.check_cancelled()

        if found_task_decorator_at_line != -1:
            if i < found_task_decorator_at_line + 3:
                use_line = found_task_decorator_at_line
                found_task_decorator_at_line = -1
                if line.startswith("def "):
                    re_match = re.match(r"\s*def\s+(\w*).*", line)
                    if re_match:
                        function_name = re_match.group(1)
                        if function_name:
                            code_lenses.append(
                                {
                                    "range": {
                                        "start": {
                                            "line": use_line,
                                            "character": 0,
                                        },
                                        "end": {
                                            "line": use_line,
                                            "character": 0,
                                        },
                                    },
                                    "command": {
                                        "title": "Run Task",
                                        "command": "robocorp.runRobocorpsPythonTask",
                                        "arguments": [
                                            [
                                                document.path,
                                                "-t",
                                                function_name,
                                            ]
                                        ],
                                    },
                                    "data": None,
                                }
                            )
                            code_lenses.append(
                                {
                                    "range": {
                                        "start": {
                                            "line": use_line,
                                            "character": 0,
                                        },
                                        "end": {
                                            "line": use_line,
                                            "character": 0,
                                        },
                                    },
                                    "command": {
                                        "title": "Debug Task",
                                        "command": "robocorp.debugRobocorpsPythonTask",
                                        "arguments": [
                                            [
                                                document.path,
                                                "-t",
                                                function_name,
                                            ]
                                        ],
                                    },
                                    "data": None,
                                }
                            )

        line = line.strip()
        if line.startswith("@task"):
            re_match = re.match(r"@\b(task)\b.*", line)
            if re_match:
                found_task_decorator_at_line = i
    return code_lenses
