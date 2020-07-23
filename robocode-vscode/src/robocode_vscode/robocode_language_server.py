from robocode_ls_core.basic import overrides, as_str
from robocode_ls_core.python_ls import PythonLanguageServer, MAX_WORKERS
from robocode_ls_core.robotframework_log import get_logger
from typing import List, Dict
from functools import partial

log = get_logger(__name__)


class RobocodeLanguageServer(PythonLanguageServer):
    def __init__(self, read_stream, write_stream, max_workers=MAX_WORKERS):
        from robocode_vscode.rcc import Rcc

        self._rcc = Rcc(self)
        PythonLanguageServer.__init__(
            self, read_stream, write_stream, max_workers=max_workers
        )

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocode_ls_core.lsp import TextDocumentSyncKind
        from robocode_vscode.commands import ALL_SERVER_COMMANDS

        server_capabilities = {
            "codeActionProvider": False,
            # "codeLensProvider": {
            #     "resolveProvider": False,  # We may need to make this configurable
            # },
            "completionProvider": {
                "resolveProvider": False  # We know everything ahead of time
            },
            "documentFormattingProvider": False,
            "documentHighlightProvider": False,
            "documentRangeFormattingProvider": False,
            "documentSymbolProvider": False,
            "definitionProvider": True,
            "executeCommandProvider": {"commands": ALL_SERVER_COMMANDS},
            "hoverProvider": False,
            "referencesProvider": False,
            "renameProvider": False,
            "foldingRangeProvider": False,
            "textDocumentSync": {
                "change": TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_workspace__execute_command(self, command=None, arguments=()):
        from robocode_vscode import commands

        if command == commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL:
            return partial(self._create_activity, arguments)

        elif command == commands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL:
            return self._list_activity_templates

    def _create_activity(self, arguments: List[Dict[str, str]]):
        import os.path
        from subprocess import CalledProcessError

        assert isinstance(arguments, list)
        assert len(arguments) == 1
        dct = next(iter(arguments))
        directory = dct["directory"]
        template = dct["template"]
        name = dct["name"]

        try:
            self._rcc.run(
                [
                    "activity",
                    "initialize",
                    "-t",
                    template,
                    "-d",
                    os.path.join(directory, name),
                ]
            )
            return {"result": "ok"}
        except CalledProcessError as e:
            stdout = as_str(e.stdout)
            stderr = as_str(e.stderr)
            msg = "Error creating activity."
            if stderr:
                msg += f"\nStderr:\n{stderr}"
            if stdout:
                msg += f"\nStdout:\n{stdout}"

            return {"result": "error", "message": msg}
        except Exception as e:
            return {"result": "error", "message": str(e)}

    def _list_activity_templates(self) -> List[str]:
        output = self._rcc.run("activity initialize -l".split())

        templates = []
        for line in output.splitlines():
            if line.startswith("- "):
                template_name = line[2:].strip()
                templates.append(template_name)

        return sorted(templates)
