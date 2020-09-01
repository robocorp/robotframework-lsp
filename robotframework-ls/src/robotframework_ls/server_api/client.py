from robocorp_ls_core.client_base import LanguageServerClientBase


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
            timeout=15 if USE_TIMEOUTS else NO_TIMEOUT,
        )

    def get_version(self):
        """
        :return:
        """
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

    def lint(self, doc_uri):
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

    def forward(self, method_name, params):
        self._check_process_alive()
        msg_id = self.next_id()
        return self.request(
            {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}
        )

    def forward_async(self, method_name, params):
        """
        :Note: async complete (returns _MessageMatcher).
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

    def request_section_name_complete(self, doc_uri, line, col):
        """
        :Note: async complete (returns _MessageMatcher).
        """
        return self.request_async(
            self._build_msg("sectionNameComplete", doc_uri=doc_uri, line=line, col=col)
        )

    def request_keyword_complete(self, doc_uri, line, col):
        """
        :Note: async complete (returns _MessageMatcher).
        """
        return self.request_async(
            self._build_msg("keywordComplete", doc_uri=doc_uri, line=line, col=col)
        )

    def request_complete_all(self, doc_uri, line, col):
        """
        Completes: sectionName, keyword, variables
        :Note: async complete (returns _MessageMatcher).
        """
        return self.request_async(
            self._build_msg("completeAll", doc_uri=doc_uri, line=line, col=col)
        )

    def request_find_definition(self, doc_uri, line, col):
        """
        :Note: async complete (returns _MessageMatcher).
        """
        return self.request_async(
            self._build_msg("findDefinition", doc_uri=doc_uri, line=line, col=col)
        )

    def request_source_format(self, text_document, options):
        """
        :Note: async complete (returns _MessageMatcher).
        """
        return self.request_async(
            self._build_msg("codeFormat", text_document=text_document, options=options)
        )
