import logging
from typing import Mapping, Any, List, Optional, Dict

from robocorp_ls_core.basic import implements
from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import (
    ILanguageServerClient,
    IIdMessageMatcher,
)
from robocorp_ls_core.lsp import (
    CodeLensTypedDict,
    CompletionsResponseTypedDict,
    CompletionItemTypedDict,
    CompletionResolveResponseTypedDict,
    PositionTypedDict,
    TextEditTypedDict,
)


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
    def initialize(
        self, root_path: str, msg_id=None, process_id=None, initialization_options=None
    ):
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
                    "initializationOptions": initialization_options,
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
        self.request(
            {
                "jsonrpc": "2.0",
                "method": "workspace/didChangeWorkspaceFolders",
                "id": self.next_id(),
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
        self.request(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "id": self.next_id(),
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

    @implements(ILanguageServerClient.close_doc)
    def close_doc(self, uri: str):
        self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/didClose",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    @implements(ILanguageServerClient.hover)
    def hover(self, uri: str, line: int, col: int):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.change_doc)
    def change_doc(self, uri: str, version: int, text: str):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/didChange",
                "params": {
                    "textDocument": {"uri": uri, "version": version},
                    "contentChanges": [{"range": None, "rangeLength": 0, "text": text}],
                },
            }
        )

    def _build_completions_request(self, uri: str, line: int, col: int):
        return {
            "jsonrpc": "2.0",
            "id": self.next_id(),
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": col},
            },
        }

    @implements(ILanguageServerClient.get_completions)
    def get_completions(
        self, uri: str, line: int, col: int
    ) -> CompletionsResponseTypedDict:
        return self.request(self._build_completions_request(uri, line, col))

    @implements(ILanguageServerClient.get_completions_async)
    def get_completions_async(
        self, uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher[CompletionsResponseTypedDict]]:
        return self.request_async(self._build_completions_request(uri, line, col))

    @implements(ILanguageServerClient.request_resolve_completion)
    def request_resolve_completion(
        self, completion_item: CompletionItemTypedDict
    ) -> CompletionResolveResponseTypedDict:
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "completionItem/resolve",
                "params": completion_item,
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

    @implements(ILanguageServerClient.request_code_action)
    def request_code_action(
        self, uri: str, line: int, col: int, endline: int, endcol: int
    ):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/codeAction",
                "params": {
                    "textDocument": {"uri": uri},
                    "range": {
                        "start": {"line": line, "character": col},
                        "end": {"line": endline, "character": endcol},
                    },
                    "context": {},
                },
            }
        )

    @implements(ILanguageServerClient.request_signature_help)
    def request_signature_help(self, uri, line, col):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/signatureHelp",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_hover)
    def request_hover(self, uri, line, col):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/hover",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_text_document_highlight)
    def request_text_document_highlight(self, uri, line, col):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/documentHighlight",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_references)
    def request_references(self, uri, line, col, include_declaration):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/references",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                    "context": {
                        "includeDeclaration": include_declaration,
                    },
                },
            }
        )

    @implements(ILanguageServerClient.request_folding_range)
    def request_folding_range(self, uri):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/foldingRange",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    @implements(ILanguageServerClient.request_on_type_formatting)
    def request_on_type_formatting(
        self, uri: str, ch: str, line: int, col: int
    ) -> Optional[List[TextEditTypedDict]]:
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/onTypeFormatting",
                "params": {
                    "textDocument": {"uri": uri},
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_selection_range)
    def request_selection_range(self, doc_uri: str, positions: List[PositionTypedDict]):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/selectionRange",
                "params": {"textDocument": {"uri": doc_uri}, "positions": positions},
            }
        )

    @implements(ILanguageServerClient.request_code_lens)
    def request_code_lens(self, uri):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/codeLens",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    @implements(ILanguageServerClient.request_resolve_code_lens)
    def request_resolve_code_lens(self, code_lens: CodeLensTypedDict):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "codeLens/resolve",
                "params": code_lens,
            }
        )

    @implements(ILanguageServerClient.request_document_symbol)
    def request_document_symbol(self, uri):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/document_symbol",
                "params": {"textDocument": {"uri": uri}},
            }
        )

    @implements(ILanguageServerClient.request_rename)
    def request_rename(self, uri: str, line: int, col: int, new_name: str):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/rename",
                "params": {
                    "textDocument": {
                        "uri": uri,
                    },
                    "position": {"line": line, "character": col},
                    "newName": new_name,
                },
            }
        )

    @implements(ILanguageServerClient.request_prepare_rename)
    def request_prepare_rename(self, uri: str, line: int, col: int):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "textDocument/prepareRename",
                "params": {
                    "textDocument": {
                        "uri": uri,
                    },
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_provide_evaluatable_expression)
    def request_provide_evaluatable_expression(
        self, uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: This is a custom message (not part of the language server spec).

        :Note: async complete.
        """
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "robot/provideEvaluatableExpression",
                "params": {
                    "uri": uri,
                    "position": {"line": line, "character": col},
                },
            }
        )

    @implements(ILanguageServerClient.request_workspace_symbols)
    def request_workspace_symbols(self, query: Optional[str] = None):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/symbol",
                "params": {"query": query},
            }
        )

    def request_cancel(self, message_id) -> None:
        """
        Requests that some processing is cancelled.
        """
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "$/cancelRequest",
                "params": {"id": message_id},
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
    def execute_command_async(
        self, command: str, arguments: list
    ) -> Optional[IIdMessageMatcher]:
        return self.request_async(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/executeCommand",
                "params": {"command": command, "arguments": arguments},
            }
        )

    @implements(ILanguageServerClient.request_sync)
    def request_sync(self, method, **params):
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": method,
                "params": params,
            }
        )

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ILanguageServerClient = check_implements(self)
