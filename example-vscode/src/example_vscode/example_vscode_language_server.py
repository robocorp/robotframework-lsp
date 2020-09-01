from robocorp_ls_core.basic import overrides
from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import IConfig

log = get_logger(__name__)


class ExampleVSCodeLanguageServer(PythonLanguageServer):
    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocorp_ls_core.lsp import TextDocumentSyncKind

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
            "executeCommandProvider": {"commands": ["extension.sayHello"]},
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
        import sys

        sys.stderr.write("Execute command: %s with args: %s\n" % (command, arguments))

    def _create_config(self) -> IConfig:
        from robocorp_ls_core.config import Config

        return Config(all_options=frozenset())
