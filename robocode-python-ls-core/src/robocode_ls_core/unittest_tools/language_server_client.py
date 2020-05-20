import logging
from robocode_ls_core.client_base import LanguageServerClientBase

log = logging.getLogger(__name__)


class _LanguageServerClient(LanguageServerClientBase):
    def __init__(self, *args, **kwargs):
        from robocode_ls_core.unittest_tools.fixtures import TIMEOUT

        LanguageServerClientBase.__init__(self, *args, **kwargs)

        self.DEFAULT_TIMEOUT = TIMEOUT

    def settings(self, settings):
        self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/didChangeConfiguration",
                "params": settings,
            }
        )

    def initialize(self, root_path, msg_id=None, process_id=None):
        from robocode_ls_core.uris import from_fs_path

        msg_id = msg_id if msg_id is not None else self.next_id()
        msg = self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {
                    "processId": process_id,
                    "rootPath": root_path,
                    "rootUri": from_fs_path(root_path),
                    "capabilities": {
                        "workspace": {
                            "applyEdit": True,
                            "didChangeConfiguration": {"dynamicRegistration": True},
                            "didChangeWatchedFiles": {"dynamicRegistration": True},
                            "symbol": {"dynamicRegistration": True},
                            "executeCommand": {"dynamicRegistration": True},
                        },
                        "textDocument": {
                            "synchronization": {
                                "dynamicRegistration": True,
                                "willSave": True,
                                "willSaveWaitUntil": True,
                                "didSave": True,
                            },
                            "completion": {
                                "dynamicRegistration": True,
                                "completionItem": {
                                    "snippetSupport": True,
                                    "commitCharactersSupport": True,
                                },
                            },
                            "hover": {"dynamicRegistration": True},
                            "signatureHelp": {"dynamicRegistration": True},
                            "definition": {"dynamicRegistration": True},
                            "references": {"dynamicRegistration": True},
                            "documentHighlight": {"dynamicRegistration": True},
                            "documentSymbol": {"dynamicRegistration": True},
                            "codeAction": {"dynamicRegistration": True},
                            "codeLens": {"dynamicRegistration": True},
                            "formatting": {"dynamicRegistration": True},
                            "rangeFormatting": {"dynamicRegistration": True},
                            "onTypeFormatting": {"dynamicRegistration": True},
                            "rename": {"dynamicRegistration": True},
                            "documentLink": {"dynamicRegistration": True},
                        },
                    },
                    "trace": "off",
                },
            }
        )

        assert "capabilities" in msg["result"]
        return msg

    def open_doc(self, uri, version=1, text=""):
        """
        :param text:
            If None, the contents will be loaded from the disk.
        """
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri,
                        "languageId": "robotframework",
                        "version": version,
                        "text": text,
                    }
                },
            }
        )

    def change_doc(self, uri, version, text):
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": uri, "version": version},
                    "contentChanges": [{"range": None, "rangeLength": 0, "text": text}],
                },
            }
        )

    def get_completions(self, uri, line, col):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/completion",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    def request_source_format(self, uri):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/formatting",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    def find_definitions(self, uri, line, col):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/definition",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )
