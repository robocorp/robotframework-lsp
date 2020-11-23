from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.basic import overrides, log_and_silence_errors
import os
import time
from robotframework_ls.constants import DEFAULT_COMPLETIONS_TIMEOUT
from robocorp_ls_core.robotframework_log import get_logger
from typing import Any, Optional, List, Dict
from robocorp_ls_core.protocols import (
    IMessageMatcher,
    IConfig,
    IWorkspace,
    IIdMessageMatcher,
    IRobotFrameworkApiClient,
    IMonitor,
)
from pathlib import Path
from robotframework_ls.ep_providers import (
    EPConfigurationProvider,
    EPDirCacheProvider,
    EPEndPointProvider,
)
from robocorp_ls_core.jsonrpc.endpoint import require_monitor
from robocorp_ls_core.jsonrpc.monitor import Monitor
from functools import partial
import itertools


log = get_logger(__name__)

LINT_DEBOUNCE_S = 0.4  # 400 ms


class _CurrLintInfo(object):
    def __init__(
        self,
        rf_lint_api_client: IRobotFrameworkApiClient,
        lsp_messages,
        doc_uri,
        is_saved,
    ) -> None:
        from robocorp_ls_core.lsp import LSPMessages

        self._rf_lint_api_client = rf_lint_api_client
        self.lsp_messages: LSPMessages = lsp_messages
        self.doc_uri = doc_uri
        self.is_saved = is_saved
        self._monitor = Monitor()

    def __call__(self) -> None:
        from robocorp_ls_core.jsonrpc.exceptions import JsonRpcRequestCancelled
        from robocorp_ls_core.client_base import wait_for_message_matcher
        from robotframework_ls.server_api.client import SubprocessDiedError

        try:
            doc_uri = self.doc_uri
            self._monitor.check_cancelled()
            found = []
            message_matcher = self._rf_lint_api_client.request_lint(doc_uri)
            if message_matcher is not None:
                if wait_for_message_matcher(
                    message_matcher,
                    monitor=self._monitor,
                    request_cancel=self._rf_lint_api_client.request_cancel,
                    timeout=60 * 3,
                ):
                    diagnostics_msg = message_matcher.msg
                    if diagnostics_msg:
                        found = diagnostics_msg.get("result", [])
                    self.lsp_messages.publish_diagnostics(doc_uri, found)
        except JsonRpcRequestCancelled:
            log.info(f"Cancelled linting: {self.doc_uri}.")

        except SubprocessDiedError:
            log.info(f"Subprocess exited while linting: {self.doc_uri}.")

        except Exception:
            log.exception("Error linting.")

    def cancel(self):
        self._monitor.cancel()


def run_in_new_thread(func, thread_name):
    import threading

    t = threading.Thread(target=func)
    t.name = thread_name
    t.start()


class _LintManager(object):
    def __init__(self, server_manager, lsp_messages) -> None:
        from robotframework_ls.server_manager import ServerManager

        self._server_manager: ServerManager = server_manager
        self._lsp_messages = lsp_messages

        self._next_id = partial(next, itertools.count())
        self._doc_id_to_info: Dict[str, _CurrLintInfo] = {}

    def schedule_lint(self, doc_uri: str, is_saved: bool) -> None:
        self.cancel_lint(doc_uri)
        rf_lint_api_client = self._server_manager.get_lint_rf_api_client(doc_uri)
        if rf_lint_api_client is None:
            log.info(f"Unable to get lint api for: {doc_uri}")
            return

        curr_info = _CurrLintInfo(
            rf_lint_api_client, self._lsp_messages, doc_uri, is_saved
        )
        from robocorp_ls_core.timeouts import TimeoutTracker

        timeout_tracker = TimeoutTracker.get_singleton()
        timeout_tracker.call_on_timeout(
            LINT_DEBOUNCE_S, partial(run_in_new_thread, curr_info, f"Lint: {doc_uri}")
        )

    def cancel_lint(self, doc_uri: str) -> None:
        curr_info = self._doc_id_to_info.pop(doc_uri, None)
        if curr_info is not None:
            curr_info.cancel()


class RobotFrameworkLanguageServer(PythonLanguageServer):
    def __init__(self, rx, tx) -> None:
        from robocorp_ls_core.pluginmanager import PluginManager
        from robotframework_ls.server_manager import ServerManager
        from robotframework_ls.ep_providers import DefaultConfigurationProvider
        from robotframework_ls.ep_providers import DefaultEndPointProvider
        from robotframework_ls.ep_providers import DefaultDirCacheProvider

        PythonLanguageServer.__init__(self, rx, tx)

        from robocorp_ls_core.cache import DirCache

        from robotframework_ls import robot_config

        home = robot_config.get_robotframework_ls_home()
        cache_dir = os.path.join(home, ".cache")

        log.debug(f"Cache dir: {cache_dir}")

        self._dir_cache = DirCache(cache_dir)

        self._pm = PluginManager()
        self._config_provider = DefaultConfigurationProvider(self.config)
        self._pm.set_instance(EPConfigurationProvider, self._config_provider)
        self._pm.set_instance(
            EPDirCacheProvider, DefaultDirCacheProvider(self._dir_cache)
        )
        self._pm.set_instance(
            EPEndPointProvider, DefaultEndPointProvider(self._endpoint)
        )
        self._server_manager = ServerManager(self._pm, language_server=self)
        self._lint_manager = _LintManager(self._server_manager, self._lsp_messages)

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robotframework_ls.robot_config import RobotConfig

        return RobotConfig()

    @overrides(PythonLanguageServer._on_workspace_set)
    def _on_workspace_set(self, workspace: IWorkspace):
        PythonLanguageServer._on_workspace_set(self, workspace)
        self._server_manager.set_workspace(workspace)

    @overrides(PythonLanguageServer._create_workspace)
    def _create_workspace(self, root_uri, workspace_folders):
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        return RobotWorkspace(root_uri, workspace_folders, generate_ast=False)

    def m_initialize(
        self,
        processId=None,
        rootUri=None,
        rootPath=None,
        initializationOptions=None,
        workspaceFolders=None,
        **_kwargs,
    ) -> dict:
        ret = PythonLanguageServer.m_initialize(
            self,
            processId=processId,
            rootUri=rootUri,
            rootPath=rootPath,
            initializationOptions=initializationOptions,
            workspaceFolders=workspaceFolders,
            **_kwargs,
        )

        initialization_options = initializationOptions
        if initialization_options:
            plugins_dir = initialization_options.get("pluginsDir")
            if isinstance(plugins_dir, str):
                if not os.path.isdir(plugins_dir):
                    log.critical(f"Expected: {plugins_dir} to be a directory.")
                else:
                    self._pm.load_plugins_from(Path(plugins_dir))

        return ret

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocorp_ls_core.lsp import TextDocumentSyncKind

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
            "executeCommandProvider": {
                "commands": ["robot.addPluginsDir", "robot.resolveInterpreter"]
            },
            "hoverProvider": False,
            "referencesProvider": False,
            "renameProvider": False,
            "foldingRangeProvider": False,
            # Note that there are no auto-trigger characters (there's no good
            # character as there's no `(` for parameters and putting it as a
            # space becomes a bit too much).
            "signatureHelpProvider": {"triggerCharacters": []},
            "textDocumentSync": {
                "change": TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
            "workspaceSymbolProvider": {"workDoneProgress": False},
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_workspace__symbol(self, query: Optional[str] = None) -> Any:
        api_client = self._server_manager.get_workspace_symbols_api_client()
        if api_client is not None:
            ret = partial(self._threaded_workspace_symbol, api_client, query)
            ret = require_monitor(ret)
            return ret

        log.info("Unable to search workspace symbols (no api available).")
        return None  # Unable to get the api.

    def _threaded_workspace_symbol(
        self,
        api_client: IRobotFrameworkApiClient,
        query: Optional[str],
        monitor: IMonitor,
    ):
        from robocorp_ls_core.client_base import wait_for_message_matcher

        # Asynchronous completion.
        message_matcher: Optional[
            IIdMessageMatcher
        ] = api_client.request_workspace_symbols(query)
        if message_matcher is None:
            log.debug("Message matcher for workspace symbols returned None.")
            return None

        if wait_for_message_matcher(
            message_matcher,
            api_client.request_cancel,
            DEFAULT_COMPLETIONS_TIMEOUT,
            monitor,
        ):
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    return result

        return None

    def m_workspace__execute_command(self, command=None, arguments=()) -> Any:
        if command == "robot.addPluginsDir":
            directory: str = arguments[0]
            assert os.path.isdir(directory), f"Expected: {directory} to be a directory."
            self._pm.load_plugins_from(Path(directory))
            return True

        elif command == "robot.resolveInterpreter":
            try:
                from robocorp_ls_core import uris
                from robotframework_ls.ep_resolve_interpreter import (
                    EPResolveInterpreter,
                )
                from robotframework_ls.ep_resolve_interpreter import IInterpreterInfo

                target_robot: str = arguments[0]

                for ep in self._pm.get_implementations(EPResolveInterpreter):
                    interpreter_info: IInterpreterInfo = ep.get_interpreter_info_for_doc_uri(
                        uris.from_fs_path(target_robot)
                    )
                    if interpreter_info is not None:
                        return {
                            "pythonExe": interpreter_info.get_python_exe(),
                            "environ": interpreter_info.get_environ(),
                            "additionalPythonpathEntries": interpreter_info.get_additional_pythonpath_entries(),
                        }
            except:
                log.exception(f"Error resolving interpreter. Args: {arguments}")

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    @log_and_silence_errors(log)
    def m_workspace__did_change_configuration(self, **kwargs):
        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        self._server_manager.set_config(self.config)

    # --- Methods to forward to the api

    @overrides(PythonLanguageServer.m_shutdown)
    @log_and_silence_errors(log)
    def m_shutdown(self, **kwargs):
        self._server_manager.shutdown()

        PythonLanguageServer.m_shutdown(self, **kwargs)

    @overrides(PythonLanguageServer.m_exit)
    @log_and_silence_errors(log)
    def m_exit(self, **kwargs):
        self._server_manager.exit()

        PythonLanguageServer.m_exit(self, **kwargs)

    def m_text_document__formatting(
        self, textDocument=None, options=None
    ) -> Optional[list]:
        source_format_rf_api_client = (
            self._server_manager.get_source_format_rf_api_client()
        )
        if source_format_rf_api_client is None:
            log.info("Unable to get API for source format.")
            return []

        message_matcher = source_format_rf_api_client.request_source_format(
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
        self._server_manager.forward(
            ("api", "lint"), "textDocument/didClose", {"textDocument": textDocument}
        )
        PythonLanguageServer.m_text_document__did_close(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_open)
    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        self._server_manager.forward(
            ("api", "lint"), "textDocument/didOpen", {"textDocument": textDocument}
        )
        PythonLanguageServer.m_text_document__did_open(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_change)
    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        self._server_manager.forward(
            ("api", "lint"),
            "textDocument/didChange",
            {"contentChanges": contentChanges, "textDocument": textDocument},
        )
        PythonLanguageServer.m_text_document__did_change(
            self, contentChanges=contentChanges, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_workspace__did_change_workspace_folders)
    def m_workspace__did_change_workspace_folders(self, event=None, **_kwargs):
        self._server_manager.forward(
            ("api", "lint"), "workspace/didChangeWorkspaceFolders", event
        )
        PythonLanguageServer.m_workspace__did_change_workspace_folders(
            self, event=event, **_kwargs
        )

    # --- Customized implementation

    @overrides(PythonLanguageServer.lint)
    def lint(self, doc_uri, is_saved) -> None:
        self._lint_manager.schedule_lint(doc_uri, is_saved)

    @overrides(PythonLanguageServer.cancel_lint)
    def cancel_lint(self, doc_uri) -> None:
        self._lint_manager.cancel_lint(doc_uri)

    def m_text_document__definition(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        if rf_api_client is not None:
            ret = partial(
                self._threaded_document_definition, rf_api_client, doc_uri, line, col
            )
            ret = require_monitor(ret)
            return ret

        log.info("Unable to find definition (no api available).")
        return None  # Unable to get the api.

    @log_and_silence_errors(log)
    def _threaded_document_definition(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        doc_uri: str,
        line: int,
        col: int,
        monitor: IMonitor,
    ) -> Optional[list]:

        from robocorp_ls_core.client_base import wait_for_message_matchers

        workspace = self.workspace
        if not workspace:
            error_msg = "Workspace is closed."
            log.critical(error_msg)
            raise RuntimeError(error_msg)

        document = workspace.get_document(doc_uri, accept_from_file=True)
        if document is None:
            error_msg = "Unable to find document (%s) for definition." % (doc_uri,)
            log.critical(error_msg)
            raise RuntimeError(error_msg)

        message_matchers: List[Optional[IIdMessageMatcher]] = [
            rf_api_client.request_find_definition(doc_uri, line, col)
        ]
        accepted_message_matchers = wait_for_message_matchers(
            message_matchers,
            monitor,
            rf_api_client.request_cancel,
            DEFAULT_COMPLETIONS_TIMEOUT,
        )
        message_matcher: IMessageMatcher
        for message_matcher in accepted_message_matchers:
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    return result

        return None

    def m_text_document__completion(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        if rf_api_client is not None:
            func = partial(
                self._threaded_document_completion, rf_api_client, doc_uri, line, col
            )
            func = require_monitor(func)
            return func

        log.info("Unable to get completions (no api available).")
        return []

    @log_and_silence_errors(log, return_on_error=[])
    def _threaded_document_completion(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        doc_uri: str,
        line: int,
        col: int,
        monitor: IMonitor,
    ) -> list:
        from robotframework_ls.impl.completion_context import CompletionContext
        from robotframework_ls.impl import section_completions
        from robotframework_ls.impl import snippets_completions
        from robocorp_ls_core.client_base import wait_for_message_matchers

        ws = self.workspace
        if not ws:
            log.critical("Workspace must be set before returning completions.")
            return []

        document = ws.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.critical("Unable to find document (%s) for completions." % (doc_uri,))
            return []

        ctx = CompletionContext(document, line, col, config=self.config)
        completions = []

        # Asynchronous completion.
        message_matchers: List[Optional[IIdMessageMatcher]] = []
        message_matchers.append(rf_api_client.request_complete_all(doc_uri, line, col))

        # These run locally (no need to get from the server).
        completions.extend(section_completions.complete(ctx))
        completions.extend(snippets_completions.complete(ctx))

        accepted_message_matchers = wait_for_message_matchers(
            message_matchers,
            monitor,
            rf_api_client.request_cancel,
            DEFAULT_COMPLETIONS_TIMEOUT,
        )
        for message_matcher in accepted_message_matchers:
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    completions.extend(result)

        return completions

    def m_text_document__signature_help(self, **kwargs):
        """
        "params": {
            "textDocument": {
                "uri": "file:///x%3A/vscode-robot/local_test/Basic/resources/keywords.robot"
            },
            "position": {"line": 7, "character": 22},
            "context": {
                "isRetrigger": False,
                "triggerCharacter": " ",
                "triggerKind": 2,
            },
        },
        """
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        if rf_api_client is not None:
            func = partial(self._signature_help, rf_api_client, doc_uri, line, col)
            func = require_monitor(func)
            return func

        log.info("Unable to get signature (no api available).")
        return []

    @log_and_silence_errors(log)
    def _signature_help(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        doc_uri: str,
        line: int,
        col: int,
        monitor: Monitor,
    ) -> Optional[dict]:
        from robocorp_ls_core.client_base import wait_for_message_matcher

        ws = self.workspace
        if not ws:
            log.critical("Workspace must be set before getting signature help.")
            return None

        document = ws.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.critical("Unable to find document (%s) for completions." % (doc_uri,))
            return None

        # Asynchronous completion.
        message_matcher: Optional[
            IIdMessageMatcher
        ] = rf_api_client.request_signature_help(doc_uri, line, col)
        if message_matcher is None:
            log.debug("Message matcher for signature returned None.")
            return None

        if wait_for_message_matcher(
            message_matcher,
            rf_api_client.request_cancel,
            DEFAULT_COMPLETIONS_TIMEOUT,
            monitor,
        ):
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    return result

        return None
