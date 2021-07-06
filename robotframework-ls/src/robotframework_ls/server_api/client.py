from typing import Optional, Dict

from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import IIdMessageMatcher, IRobotFrameworkApiClient
from robocorp_ls_core.lsp import (
    TextDocumentTypedDict,
    ResponseTypedDict,
    PositionTypedDict,
    CodeLensTypedDict,
)
from robocorp_ls_core.basic import implements


class SubprocessDiedError(Exception):
    pass


class RobotFrameworkApiClient(LanguageServerClientBase):
    def __init__(self, writer, reader, server_process):
        LanguageServerClientBase.__init__(self, writer, reader)
        self.server_process = server_process
        self._check_process_alive()
        self._version = None

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
        self, msg_id=None, process_id=None, root_uri=u"", workspace_folders=()
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
        self, prefix: str, full_code: str, indent: str
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

    def request_section_name_complete(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("sectionNameComplete", doc_uri=doc_uri, line=line, col=col)
        )

    def request_keyword_complete(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("keywordComplete", doc_uri=doc_uri, line=line, col=col)
        )

    def request_complete_all(self, doc_uri, line, col) -> Optional[IIdMessageMatcher]:
        """
        Completes: sectionName, keyword, variables
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("completeAll", doc_uri=doc_uri, line=line, col=col)
        )

    def request_find_definition(
        self, doc_uri, line, col
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("findDefinition", doc_uri=doc_uri, line=line, col=col)
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

    def request_hover(
        self, doc_uri: str, line: int, col: int
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(
            self._build_msg("hover", doc_uri=doc_uri, line=line, col=col)
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

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IRobotFrameworkApiClient = check_implements(self)
