from robocorp_ls_core.basic import overrides
from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import IConfig

log = get_logger(__name__)

TOKEN_TYPES = [
    "namespace",
    "type",
    "class",
    "enum",
    "interface",
    "struct",
    "typeParameter",
    "parameter",
    "variable",
    "property",
    "enumMember",
    "event",
    "function",
    "method",
    "macro",
    "keyword",
    "modifier",
    "comment",
    "string",
    "number",
    "regexp",
    "operator",
]

TOKEN_MODIFIERS = [
    "declaration",
    "definition",
    "readonly",
    "static",
    "deprecated",
    "abstract",
    "async",
    "modification",
    "documentation",
    "defaultLibrary",
]


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
            "definitionProvider": False,
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
            "semanticTokensProvider": {
                "legend": {
                    "tokenTypes": TOKEN_TYPES,
                    "tokenModifiers": TOKEN_MODIFIERS,
                },
                "range": False,
                "full": False,
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_workspace__execute_command(self, command=None, arguments=()):
        import sys

        sys.stderr.write("Execute command: %s with args: %s\n" % (command, arguments))

    def m_text_document__semantic_tokens__full(self, textDocument=None):
        # # deltaLine: 1, deltaCol: 0, len: 10, tokenType: 2 (class), tokenModifier: 0 (none)
        # # deltaLine: 1, deltaCol: 0, len: 10, tokenType: 2 (class), tokenModifier: 0 (none)
        # return {"data": [1, 0, 10, 1, 0, 1, 0, 10, 1, 0]}
        return {"data": []}

    def lint(self, doc_uri, is_saved, content_changes=None):
        pass

    def cancel_lint(self, doc_uri):
        pass

    def _create_config(self) -> IConfig:
        from robocorp_ls_core.config import Config

        return Config(all_options=frozenset())
