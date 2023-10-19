from typing import Optional, Dict, List

from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import (
    IIdMessageMatcher,
    IRobotFrameworkApiClient,
    ILanguageServerClientBase,
)
from robocorp_ls_core.lsp import (
    TextDocumentTypedDict,
    ResponseTypedDict,
    PositionTypedDict,
    CodeLensTypedDict,
    CompletionItemTypedDict,
    CompletionsResponseTypedDict,
    CompletionResolveResponseTypedDict,
    TextDocumentCodeActionTypedDict,
)
from robocorp_ls_core.basic import implements


class SubprocessDiedError(Exception):
    pass


class RobotFrameworkApiClient(LanguageServerClientBase):
    def __init__(
        self, writer, reader, server_process, on_received_message=None
    ) -> None:
        LanguageServerClientBase.__init__(
            self, writer, reader, on_received_message=on_received_message
        )
        self.server_process = server_process
        self._check_process_alive()
        self._version = None

        self.stats: Dict[str, int] = {}

    @implements(ILanguageServerClientBase.write)
    def write(self, contents):
        if isinstance(contents, dict):
            method = contents.get("method")
            if method:
                self.stats[method] = self.stats.get(method, 0) + 1
        return LanguageServerClientBase.write(self, contents)

    def _check_process_alive(self, raise_exception=True):
        returncode = self.server_process.poll()
        if returncode is not None:
            if raise_exception:
                raise SubprocessDiedError(
                    "Process has already exited. Stderr: %s"
                    % (self.server_process.stderr.read())
                )
            return False
        return True

    def initialize(
        self, msg_id=None, process_id=None, root_uri="", workspace_folders=()
    ):
        from robocorp_ls_core.options import NO_TIMEOUT, USE_TIMEOUTS

        self._check_process_alive()
        msg_id = msg_id if msg_id is not None else self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {
                    "processId": process_id,
                    "rootUri": root_uri,
                    "workspaceFolders": workspace_folders,
                },
            },
            timeout=30 if USE_TIMEOUTS else NO_TIMEOUT,
        )

    @implements(IRobotFrameworkApiClient.settings)
    def settings(self, settings: Dict):
        self.request(
            {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "workspace/didChangeConfiguration",
                "params": settings,
            }
        )

    def get_version(self) -> str:
        if self._version is None:
            self._check_process_alive()
            msg_id = self.next_id()
            msg = self.request(
                {"jsonrpc": "2.0", "id": msg_id, "method": "version"}, None
            )
            if msg is None:
                self._check_process_alive()
                return "Unable to get version."

            version = msg.get("result", "N/A")
            self._version = version
            return version

        return self._version

    @implements(IRobotFrameworkApiClient.lint)
    def lint(self, doc_uri) -> ResponseTypedDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "lint",
                "params": {"doc_uri": doc_uri},
            },
            default=[],
        )

    def request_lint(self, doc_uri: str) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("lint", doc_uri=doc_uri))

    def request_semantic_tokens_full(
        self, text_document: TextDocumentTypedDict
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "textDocument/semanticTokens/full", textDocument=text_document
            )
        )

    def request_semantic_tokens_from_code_full(
        self, prefix: str, full_code: str, indent: str, uri: str
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "semanticTokensFromCodeFull",
                prefix=prefix,
                full_code=full_code,
                indent=indent,
                uri=uri,
            )
        )

    def request_monaco_completions_from_code(
        self,
        prefix: str,
        full_code: str,
        position: PositionTypedDict,
        uri: str,
        indent: str,
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "monacoCompletionsFromCodeFull",
                prefix=prefix,
                full_code=full_code,
                position=position,
                uri=uri,
                indent=indent,
            )
        )

    def request_monaco_resolve_completion(
        self,
        completion_item: CompletionItemTypedDict,
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "monacoResolveCompletion",
                completion_item=completion_item,
            )
        )

    def forward(self, method_name, params):
        self._check_process_alive()
        msg_id = self.next_id()
        return self.request(
            {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}
        )

    def forward_async(self, method_name, params) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        self._check_process_alive()
        msg_id = self.next_id()
        return self.request_async(
            {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}
        )

    def open(self, uri, version, source):
        self.forward(
            "textDocument/didOpen",
            {"textDocument": {"uri": uri, "version": version, "text": source}},
        )

    def _build_msg(self, method_name, **params):
        self._check_process_alive()
        msg_id = self.next_id()
        return {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}

    def request_complete_all(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher[CompletionsResponseTypedDict]]:
        """
        Completes: sectionName, keyword, variables
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("completeAll", doc_uri=doc_uri, line=line, col=col)
        )

    def request_resolve_completion_item(
        self, completion_item: CompletionItemTypedDict
    ) -> Optional[IIdMessageMatcher[CompletionResolveResponseTypedDict]]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("resolveCompletionItem", completion_item=completion_item)
        )

    def request_flow_explorer_model(self, uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("flowExplorerModel", uri=uri))

    def request_find_definition(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("findDefinition", doc_uri=doc_uri, line=line, col=col)
        )

    def request_rename(
        self, doc_uri: str, line: int, col: int, new_name: str
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "rename", doc_uri=doc_uri, line=line, col=col, new_name=new_name
            )
        )

    def request_prepare_rename(
        self, doc_uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("prepareRename", doc_uri=doc_uri, line=line, col=col)
        )

    def request_source_format(
        self, text_document, options
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("codeFormat", text_document=text_document, options=options)
        )

    def request_signature_help(self, doc_uri, line, col) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("signatureHelp", doc_uri=doc_uri, line=line, col=col)
        )

    def request_folding_range(self, doc_uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("foldingRange", doc_uri=doc_uri))

    def request_on_type_formatting(
        self, doc_uri: str, ch: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "onTypeFormatting", doc_uri=doc_uri, ch=ch, line=line, col=col
            )
        )

    def request_selection_range(
        self, doc_uri, positions: List[PositionTypedDict]
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("selectionRange", doc_uri=doc_uri, positions=positions)
        )

    def request_code_lens(self, doc_uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("codeLens", doc_uri=doc_uri))

    def request_resolve_code_lens(
        self, code_lens: CodeLensTypedDict
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("resolveCodeLens", **code_lens))

    def request_document_symbol(self, doc_uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("documentSymbol", doc_uri=doc_uri))

    def request_list_tests(self, doc_uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("listTests", doc_uri=doc_uri))

    def request_wait_for_full_test_collection(self) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("waitForFullTestCollection"))

    def request_evaluatable_expression(
        self, doc_uri, position
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("evaluatableExpression", doc_uri=doc_uri, position=position)
        )

    def request_collect_robot_documentation(
        self,
        doc_uri,
        library_name: Optional[str] = None,
        line: Optional[int] = None,
        col: Optional[int] = None,
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "collectRobotDocumentation",
                doc_uri=doc_uri,
                library_name=library_name,
                line=line,
                col=col,
            )
        )

    def request_rf_info(self, doc_uri) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("rfInfo", doc_uri=doc_uri))

    def request_hover(
        self, doc_uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("hover", doc_uri=doc_uri, line=line, col=col)
        )

    def request_document_highlight(
        self, doc_uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("document_highlight", doc_uri=doc_uri, line=line, col=col)
        )

    def request_code_action(
        self, doc_uri: str, params: TextDocumentCodeActionTypedDict
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("code_action", doc_uri=doc_uri, params=params)
        )

    def request_references(
        self, doc_uri: str, line: int, col: int, include_declaration: bool
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg(
                "references",
                doc_uri=doc_uri,
                line=line,
                col=col,
                include_declaration=include_declaration,
            )
        )

    def request_workspace_symbols(
        self, query: Optional[str] = None
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg("workspaceSymbols", query=query))

    def request_cancel(self, message_id):
        self._check_process_alive()
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "$/cancelRequest",
                "params": dict(id=message_id),
            }
        )

    def request_sync(self, method, **params):
        """
        This API is is a bit simpler than the `request` as it builds the message
        internally.
        """
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

        _: IRobotFrameworkApiClient = check_implements(self)
