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
from functools import partial
import itertools
import time
from robotframework_ls.constants import DEFAULT_COMPLETIONS_TIMEOUT
from robotframework_ls.robotframework_log import get_logger


log = get_logger(__name__)

LINT_DEBOUNCE_S = 0.5  # 500 ms
ROBOT_FILE_EXTENSIONS = (".robot", ".settings")
_next_id = partial(next, itertools.count(0))


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
        self._initializing = False

    @property
    def robot_framework_language_server(self):
        return self._robot_framework_language_server()

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
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_PYTHON_EXECUTABLE,
        )

        config = self._config
        python_exe = sys.executable
        if config is not None:
            python_exe = config.get_setting(
                OPTION_ROBOT_PYTHON_EXECUTABLE, str, default=python_exe
            )
        else:
            log.warning("self._config not set in %s" % (self.__class__,))
        return python_exe

    def _get_environ(self):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV

        config = self._config
        env = os.environ.copy()

        env.pop("PYTHONPATH", "")
        env.pop("PYTHONHOME", "")
        env.pop("VIRTUAL_ENV", "")

        if config is not None:
            env_in_settings = config.get_setting(
                OPTION_ROBOT_PYTHON_ENV, dict, default={}
            )
            for key, val in env_in_settings.items():
                env[str(key)] = str(val)
        else:
            log.warning("self._config not set in %s" % (self.__class__,))
        return env

    def _get_server_api(self):
        with self._server_lock:
            server_process = self._server_process

            if server_process is not None:
                # If someone killed it, dispose of internal references
                # and create a new process.
                if not is_process_alive(server_process.pid):
                    server_process = None
                    self._dispose_server_process()

            if server_process is None:
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
                        JsonRpcStreamReader,
                    )

                    args = []
                    if Setup.options.verbose:
                        args.append("-" + "v" * int(Setup.options.verbose))
                    if Setup.options.log_file:
                        log_id = _next_id()
                        # i.e.: use a log id in case we create more than one in the
                        # same session.
                        if log_id == 0:
                            args.append("--log-file=" + Setup.options.log_file + ".api")
                        else:
                            args.append(
                                "--log-file="
                                + Setup.options.log_file
                                + (".%s" % (log_id,))
                                + ".api"
                            )

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

                    api = self._server_api = RobotFrameworkApiClient(
                        w, r, server_process
                    )
                    api.initialize(
                        process_id=os.getpid(),
                        root_uri=self._workspace.root_uri,
                        workspace_folders=list(
                            {"uri": folder.uri, "name": folder.name}
                            for folder in list(self._workspace.folders.values())
                        ),
                    )

                    # Open existing documents in the API.
                    for document in self._workspace.iter_documents():
                        api.forward(
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
                    if server_process is None:
                        log.exception(
                            "Error starting robotframework server api (server_process=None)."
                        )
                    else:
                        exitcode = server_process.poll()
                        if exitcode is not None:
                            # Note: only read() if the process exited.
                            log.exception(
                                "Error starting robotframework server api. Exit code: %s Base exception: %s. Stderr: %s"
                                % (exitcode, e, server_process.stderr.read())
                            )
                        else:
                            log.exception(
                                "Error (%s) starting robotframework server api (still running). Base exception: %s."
                                % (exitcode, e)
                            )
                    self._dispose_server_process()
                finally:
                    if server_process is not None:
                        log.debug(
                            "Server api (%s) created pid: %s"
                            % (self, server_process.pid)
                        )

        return self._server_api

    @log_and_silence_errors(log)
    def _dispose_server_process(self):
        with self._server_lock:
            try:
                log.debug("Dispose server process.")
                if self._server_process is not None:
                    if is_process_alive(self._server_process.pid):
                        kill_process_and_subprocesses(self._server_process.pid)
            finally:
                self._server_process = None
                self._server_api = None
                self._used_environ = None
                self._used_python_executable = None

    def lint(self, doc_uri):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.lint(doc_uri)

    def request_section_name_complete(self, doc_uri, line, col):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.request_section_name_complete(doc_uri, line, col)

    def request_keyword_complete(self, doc_uri, line, col):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.request_keyword_complete(doc_uri, line, col)

    def request_complete_all(self, doc_uri, line, col):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.request_complete_all(doc_uri, line, col)

    def request_find_definition(self, doc_uri, line, col):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.request_find_definition(doc_uri, line, col)

    def request_source_format(self, text_document, options):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.request_source_format(text_document, options)

    @log_and_silence_errors(log)
    def forward(self, method_name, params):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                api.forward(method_name, params)

    @log_and_silence_errors(log)
    def open(self, uri, version, source):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                api.open(uri, version, source)

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

    @overrides(PythonLanguageServer._create_workspace)
    def _create_workspace(self, root_uri, workspace_folders):
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        return RobotWorkspace(root_uri, workspace_folders, generate_ast=False)

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
            "documentFormattingProvider": True,
            "documentHighlightProvider": False,
            "documentRangeFormattingProvider": False,
            "documentSymbolProvider": False,
            "definitionProvider": True,
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

    def m_text_document__formatting(self, textDocument=None, options=None):
        message_matcher = self._api.request_source_format(
            text_document=textDocument, options=options
        )
        if message_matcher is None:
            raise RuntimeError(
                "Error requesting code formatting (message_matcher==None)."
            )
        curtime = time.time()
        maxtime = curtime + DEFAULT_COMPLETIONS_TIMEOUT

        # i.e.: wait X seconds for the code format and bail out if we
        # can't get it.
        available_time = maxtime - time.time()
        if available_time <= 0:
            raise RuntimeError("Code formatting timed-out (available_time <= 0).")

        if message_matcher.event.wait(available_time):
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    return result
                else:
                    return []
        raise RuntimeError("Code formatting timed-out.")

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
            found = []
            diagnostics_msg = self._api.lint(doc_uri)
            if diagnostics_msg:
                found = diagnostics_msg.get("result", [])
            self._lsp_messages.publish_diagnostics(doc_uri, found)
        except Exception:
            # Because it's debounced, we can't use the log_and_silence_errors decorator.
            log.exception("Error linting.")

    def m_text_document__definition(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        document = self.workspace.get_document(doc_uri, create=False)
        if document is None:
            msg = "Unable to find document (%s) for completions." % (doc_uri,)
            log.critical(msg)
            raise RuntimeError(msg)

        message_matchers = [self._api.request_find_definition(doc_uri, line, col)]
        accepted_message_matchers = self._wait_for_message_matchers(message_matchers)
        for message_matcher in accepted_message_matchers:
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    return result

        return None

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

        ctx = CompletionContext(document, line, col, config=self.config)
        completions = []

        # Asynchronous completion.
        message_matchers = []
        message_matchers.append(self._api.request_complete_all(doc_uri, line, col))
        completions.extend(section_completions.complete(ctx))

        accepted_message_matchers = self._wait_for_message_matchers(message_matchers)
        for message_matcher in accepted_message_matchers:
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    completions.extend(result)

        return completions

    def _wait_for_message_matchers(self, message_matchers):
        accepted_message_matchers = []
        curtime = time.time()
        maxtime = curtime + DEFAULT_COMPLETIONS_TIMEOUT
        for message_matcher in message_matchers:
            if message_matcher is not None:
                # i.e.: wait X seconds and bail out if we can't get it.
                available_time = maxtime - time.time()
                if available_time <= 0:
                    available_time = 0.0001  # Wait at least a bit for each.

                if message_matcher.event.wait(available_time):
                    accepted_message_matchers.append(message_matcher)

        return accepted_message_matchers
