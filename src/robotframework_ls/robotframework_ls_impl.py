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


log = logging.getLogger(__name__)

LINT_DEBOUNCE_S = 0.5  # 500 ms
ROBOT_FILE_EXTENSIONS = (".robot", ".settings")


class _ServerApi(object):
    def __init__(self):
        self._server_lock = threading.RLock()

        self._used_python_executable = None
        self._server_process = None
        self._server_api = None  # :type self._server_api: RobotFrameworkApiClient
        self.config = None

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

    def _get_server_api(self):
        import os

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
                        self._used_python_executable = python_exe
                        server_process = start_server_process(
                            args=args, python_exe=python_exe
                        )

                        self._server_process = server_process

                        write_to = server_process.stdin
                        read_from = server_process.stdout
                        w = JsonRpcStreamWriter(write_to, sort_keys=True)
                        r = JsonRpcStreamReader(read_from)

                        self._server_api = RobotFrameworkApiClient(w, r, server_process)
                        self._server_api.initialize(process_id=os.getpid())
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
                self._used_python_executable = None

    def lint(self, source):
        with self._server_lock:
            api = self._get_server_api()
            if api is not None:
                return api.lint(source)

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

        self._api = _ServerApi()
        PythonLanguageServer.__init__(self, rx, tx)
        self._lsp_messages = LSPMessages(self._endpoint)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config
        self._api.config = self.config

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    @log_and_silence_errors(log)
    def m_workspace__did_change_configuration(self, **kwargs):
        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        self._api.config = self.config

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

    @overrides(PythonLanguageServer.lint)
    @_utils.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved):
        # Since we're debounced, the document may no longer be open
        try:
            workspace = self._match_uri_to_workspace(doc_uri)
            if doc_uri in workspace.documents:
                document = workspace.get_document(doc_uri)

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

        workspace = self._match_uri_to_workspace(doc_uri)
        if doc_uri in workspace.documents:
            document = workspace.get_document(doc_uri)

        ctx = CompletionContext(document, line, col)
        completions = []
        completions.extend(section_completions.complete(ctx))
        return completions

    @overrides(PythonLanguageServer.m_workspace__did_change_watched_files)
    @log_and_silence_errors(log)
    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        changed_files = set()
        for d in changes or []:
            if d["uri"].endswith(ROBOT_FILE_EXTENSIONS):
                changed_files.add(d["uri"])

        if not changed_files:
            # Only externally changed robot files may result in changed diagnostics.
            return

        for workspace_uri in self.workspaces:
            workspace = self.workspaces[workspace_uri]
            for doc_uri in workspace.documents:
                # Changes in doc_uri are already handled by m_text_document__did_save
                if doc_uri not in changed_files:
                    self.lint(doc_uri, is_saved=False)
