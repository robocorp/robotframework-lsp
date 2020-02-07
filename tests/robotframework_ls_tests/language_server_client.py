import logging
from robotframework_ls.client_base import LanguageServerClientBase

log = logging.getLogger(__name__)


class _LanguageServerClient(LanguageServerClientBase):
    def __init__(self, *args, **kwargs):
        LanguageServerClientBase.__init__(self, *args, **kwargs)
        from robotframework_ls_tests import conftest

        self.TIMEOUT = conftest.TIMEOUT

    def initialize(self, root_path, msg_id=None, process_id=None):
        from robotframework_ls.uris import from_fs_path

        msg_id = msg_id if msg_id is not None else self.next_id()
        self.write(
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

        msg = self.wait_for_message({"id": msg_id})
        assert "capabilities" in msg["result"]
        return msg
