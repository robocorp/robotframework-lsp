from robotframework_ls import _utils
from robotframework_ls.python_ls import PythonLanguageServer
import threading
import logging
from robotframework_ls._utils import (
    overrides,
    log_and_silence_errors,
    kill_process_and_subprocesses,
    is_process_alive,
)
import sys
import weakref
import os


log = logging.getLogger(__name__)

LINT_DEBOUNCE_S = 0.5  # 500 ms
ROBOT_FILE_EXTENSIONS = (".robot", ".settings")


class _ServerApi(object):
    def __init__(self, robot_framework_language_server):
        self._server_lock = threading.RLock()

        self._used_python_executable = None
        self._used_environ = None
        self._server_process = None
        self._server_api = None  # :type self._server_api: RobotFrameworkApiClient
        self.config = None
        self._robot_framework_language_server = weakref.ref(
            robot_framework_language_server
        )

    @property
    def _workspace(self):
        ls = self._robot_framework_language_server()
        if ls is None:
            return None

        return ls.workspace

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        with self._server_lock:
            # If the python executable changes, restart the server API.
            if self._used_python_executable is not None:
                python_executable = self._get_python_executable()
                if python_executable != self._used_python_executable:
                    # It'll be reinitialized when needed.
                    self._dispose_server_process()
                    return
            if self._used_environ is not None:
                environ = self._get_environ()
                if environ != self._used_environ:
                    # It'll be reinitialized when needed.
                    self._dispose_server_process()
                    return

    def _get_python_executable(self):
        config = self._config
        python_exe = sys.executable
        if config is not None:
            python_exe = config.get_setting(
                "robot.python.executable", str, default=python_exe
            )
        else:
            log.warning("self._config not set in %s" % (self.__class__,))
        return python_exe

    def _get_environ(self):
        config = self._config
        env = os.environ.copy()

        env.pop("PYTHONPATH", "")
        env.pop("PYTHONHOME", "")
        env.pop("VIRTUAL_ENV", "")

        if config is not None:
            env_in_settings = config.get_setting("robot.python.env", dict, default={})
            for key, val in env_in_settings.items():
                env[str(key)] = str(val)
        else:
            log.warning("self._config not set in %s" % (self.__class__,))
        return env

    def _get_server_api(self):
        server_process = self._server_process
        if server_process is None or not is_process_alive(server_process.pid):
            with self._server_lock:
                # Check again with lock.
                if self._server_process is not None:
                    # If someone killed it, dispose of internal references
                    # and create a new process.
                    if not is_process_alive(self._server_process.pid):
                        self._dispose_server_process()

                if self._server_process is None:
                    try:
                        from robotframework_ls.options import Setup
                        from robotframework_ls.server_api.client import (
                            RobotFrameworkApiClient,
                        )
                        from robotframework_ls.server_api.server__main__ import (
                            start_server_process,
                        )
                        from robotframework_ls.jsonrpc.streams import (
                            JsonRpcStreamWriter,
                        )
                        from robotframework_ls.jsonrpc.streams import (
                            JsonRpcStreamReader,
                        )

                        args = []
                        if Setup.options.verbose:
                            args.append("-" + "v" * int(Setup.options.verbose))
                        if Setup.options.log_file:
                            args.append("--log-file=" + Setup.options.log_file + ".api")

                        python_exe = self._get_python_executable()
                        environ = self._get_environ()

                        self._used_python_executable = python_exe
                        self._used_environ = environ

                        server_process = start_server_process(
                            args=args, python_exe=python_exe, env=environ
                        )

                        self._server_process = server_process

                        write_to = server_process.stdin
                        read_from = server_process.stdout
                        w = JsonRpcStreamWriter(write_to, sort_keys=True)
                        r = JsonRpcStreamReader(read_from)

                        self._server_api = RobotFrameworkApiClient(w, r, server_process)
                        self._server_api.initialize(process_id=os.getpid())

                        # Open existing documents in the API.
                        for document in self._workspace.iter_documents():
                            self.forward(
                                "textDocument/didOpen",
                                {
                                    "textDocument": {
                                        "uri": document.uri,
                                        "version": document.version,
                                        "text": document.source,
                                    }
                                },
                            )

                    except Exception as e:
                        if server_process is not None:
                            log.exception(
                                "Error starting robotframework server api (server_process=None)."
                            )
                        else:
                            log.exception(
                                "Error starting robotframework server api. Exit code: %s Base exception: %s. Stderr: %s"
                                % (
                                    server_process.returncode,
                                    e,
                                    server_process.stderr.read(),
                                )
                            )
                        self._dispose_server_process()

        return self._server_api

    @log_and_silence_errors(log)
    def _dispose_server_process(self):
        with self._server_lock:
            try:
                if self._server_process is not None:
                    if is_process_alive(self._server_process.pid):
                        kill_process_and_subprocesses(self._server_process.pid)
            finally:
                self._server_process = None
                self._server_api = None
                self._used_environ = None
                self._used_python_executable = None

    def lint(self, source):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.lint(source)

    @log_and_silence_errors(log)
    def forward(self, method_name, params):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                api.forward(method_name, params)

    @log_and_silence_errors(log)
    def exit(self):
        with self._server_lock:
            if self._server_api is not None:
                # i.e.: only exit if it was started in the first place.
                self._server_api.exit()
            self._dispose_server_process()

    @log_and_silence_errors(log)
    def shutdown(self):
        with self._server_lock:
            if self._server_api is not None:
                # i.e.: only shutdown if it was started in the first place.
                self._server_api.shutdown()


class RobotFrameworkLanguageServer(PythonLanguageServer):
    def __init__(self, rx, tx):
        from robotframework_ls.lsp import LSPMessages

        self._api = _ServerApi(self)
        PythonLanguageServer.__init__(self, rx, tx)
        self._lsp_messages = LSPMessages(self._endpoint)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        self._api.config = self.config

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robotframework_ls import lsp

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
            "executeCommandProvider": {"commands": []},
            "hoverProvider": False,
            "referencesProvider": False,
            "renameProvider": False,
            "foldingRangeProvider": False,
            # "signatureHelpProvider": {
            #     'triggerCharacters': ['(', ',', '=']
            # },
            "textDocumentSync": {
                "change": lsp.TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    @log_and_silence_errors(log)
    def m_workspace__did_change_configuration(self, **kwargs):
        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        self._api.config = self.config

    # --- Methods to forward to the api

    @overrides(PythonLanguageServer.m_shutdown)
    @log_and_silence_errors(log)
    def m_shutdown(self, **kwargs):
        self._api.shutdown()
        PythonLanguageServer.m_shutdown(self, **kwargs)

    @overrides(PythonLanguageServer.m_exit)
    @log_and_silence_errors(log)
    def m_exit(self, **kwargs):
        self._api.exit()
        PythonLanguageServer.m_exit(self, **kwargs)

    @overrides(PythonLanguageServer.m_text_document__did_close)
    def m_text_document__did_close(self, textDocument=None, **_kwargs):
        self._api.forward("textDocument/didClose", {"textDocument": textDocument})
        PythonLanguageServer.m_text_document__did_close(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_open)
    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        self._api.forward("textDocument/didOpen", {"textDocument": textDocument})
        PythonLanguageServer.m_text_document__did_open(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_change)
    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        self._api.forward(
            "textDocument/didChange",
            {"contentChanges": contentChanges, "textDocument": textDocument},
        )
        PythonLanguageServer.m_text_document__did_change(
            self, contentChanges=contentChanges, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_workspace__did_change_workspace_folders)
    def m_workspace__did_change_workspace_folders(
        self, added=None, removed=None, **_kwargs
    ):
        self._api.forward(
            "workspace/didChangeWorkspaceFolders", {"added": added, "removed": removed}
        )
        PythonLanguageServer.m_workspace__did_change_workspace_folders(
            self, added=added, removed=removed, **_kwargs
        )

    # --- Customized implementation

    @overrides(PythonLanguageServer.lint)
    @_utils.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved):
        # Since we're debounced, the document may no longer be open
        try:
            document = self.workspace.get_document(doc_uri, create=False)
            if document is None:
                return

            source = document.source
            found = []
            diagnostics_msg = self._api.lint(source)
            if diagnostics_msg:
                found = diagnostics_msg.get("result", [])
            self._lsp_messages.publish_diagnostics(doc_uri, found)
        except Exception:
            # Because it's debounced, we can't use the log_and_silence_errors decorator.
            log.exception("Error linting.")

    @log_and_silence_errors(log, return_on_error=[])
    def m_text_document__completion(self, **kwargs):
        from robotframework_ls.impl.completion_context import CompletionContext
        from robotframework_ls.impl import section_completions

        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        document = self.workspace.get_document(doc_uri, create=False)
        if document is None:
            log.critical("Unable to find document (%s) for completions." % (doc_uri,))
            return []

        ctx = CompletionContext(document, line, col)
        completions = []
        completions.extend(section_completions.complete(ctx))
        return completions
