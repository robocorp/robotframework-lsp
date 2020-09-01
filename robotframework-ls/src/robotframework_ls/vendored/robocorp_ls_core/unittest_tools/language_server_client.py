import logging
from typing import Mapping, Any, List, Optional, Dict

from robocorp_ls_core.basic import implements
from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import ILanguageServerClient, IMessageMatcher


log = logging.getLogger(__name__)


class LanguageServerClient(LanguageServerClientBase):
    pid: Optional[int] = None

    DEFAULT_TIMEOUT: Optional[int] = None

    def __init__(self, *args, **kwargs):
        from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

        LanguageServerClientBase.__init__(self, *args, **kwargs)

        self.DEFAULT_TIMEOUT = TIMEOUT

    @implements(ILanguageServerClient.settings)
    def settings(self, settings: Dict):
        self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/didChangeConfiguration",
                "params": settings,
            }
        )

    @implements(ILanguageServerClient.initialize)
    def initialize(self, root_path: str, msg_id=None, process_id=None):
        from robocorp_ls_core.uris import from_fs_path

        root_uri = from_fs_path(root_path)

        msg_id = msg_id if msg_id is not None else self.next_id()
        msg = self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {
                    "processId": process_id,
                    "rootPath": root_path,
                    "rootUri": root_uri,
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

    @implements(ILanguageServerClient.change_workspace_folders)
    def change_workspace_folders(
        self, added_folders: List[str], removed_folders: List[str]
    ) -> None:
        from robocorp_ls_core import uris
        import os.path

        added_folders_uri_name = [
            {"uri": uris.from_fs_path(s), "name": os.path.basename(s)}
            for s in added_folders
        ]
        removed_folders_uri_name = [
            {"uri": uris.from_fs_path(s), "name": os.path.basename(s)}
            for s in removed_folders
        ]
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "workspace/didChangeWorkspaceFolders",
                "params": {
                    "event": {
                        "added": added_folders_uri_name,
                        "removed": removed_folders_uri_name,
                    }
                },
            }
        )

    @implements(ILanguageServerClient.open_doc)
    def open_doc(self, uri: str, version: int = 1, text: Optional[str] = None):
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

    @implements(ILanguageServerClient.change_doc)
    def change_doc(self, uri: str, version: int, text: str):
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

    @implements(ILanguageServerClient.get_completions)
    def get_completions(self, uri: str, line: int, col: int):
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

    @implements(ILanguageServerClient.request_source_format)
    def request_source_format(self, uri: str):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/formatting",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    @implements(ILanguageServerClient.find_definitions)
    def find_definitions(self, uri, line: int, col: int):
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

    @implements(ILanguageServerClient.execute_command)
    def execute_command(self, command: str, arguments: list) -> Mapping[str, Any]:
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/executeCommand",
                "params": {"command": command, "arguments": arguments},
            }
        )

    @implements(ILanguageServerClient.execute_command_async)
    def execute_command_async(self, command: str, arguments: list) -> IMessageMatcher:
        return self.request_async(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/executeCommand",
                "params": {"command": command, "arguments": arguments},
            }
        )

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ILanguageServerClient = check_implements(self)
