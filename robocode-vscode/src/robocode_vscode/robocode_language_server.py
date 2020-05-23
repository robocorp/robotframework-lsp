from robocode_ls_core.basic import overrides
from robocode_ls_core.python_ls import PythonLanguageServer
from robocode_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class RobocodeLanguageServer(PythonLanguageServer):
    def __init__(self, rx, tx):
        PythonLanguageServer.__init__(self, rx, tx)

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocode_ls_core.lsp import TextDocumentSyncKind

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
            "executeCommandProvider": {"commands": ["robocode.sayHello"]},
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
        if command == "robocode.sayHello":
            self._lsp_messages.show_message("Hello World")
