from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.basic import overrides, log_and_silence_errors
import os
import time
from robotframework_ls.constants import DEFAULT_COMPLETIONS_TIMEOUT
from robocorp_ls_core.robotframework_log import get_logger
from typing import Any, Optional, Dict
from robocorp_ls_core.protocols import (
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
from functools import partial
import itertools
from robotframework_ls import __version__, rf_interactive_integration
import typing
import sys
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from robocorp_ls_core.lsp import (
    CodeLensTypedDict,
    TextDocumentPositionParamsTypedDict,
    PositionTypedDict,
    CompletionItemTypedDict,
)
from robotframework_ls.commands import (
    ROBOT_GET_RFLS_HOME_DIR,
    ROBOT_START_INDEXING_INTERNAL,
    ROBOT_WAIT_FULL_TEST_COLLECTION_INTERNAL,
)


log = get_logger(__name__)

_LINT_DEBOUNCE_IN_SECONDS_LOW = 0.2
_LINT_DEBOUNCE_IN_SECONDS_HIGH = 0.8


class _CurrLintInfo(object):
    def __init__(
        self,
        rf_lint_api_client: IRobotFrameworkApiClient,
        lsp_messages,
        doc_uri,
        is_saved,
        on_finish,
    ) -> None:
        from robocorp_ls_core.lsp import LSPMessages
        from robocorp_ls_core.jsonrpc.monitor import Monitor

        self._rf_lint_api_client = rf_lint_api_client
        self.lsp_messages: LSPMessages = lsp_messages
        self.doc_uri = doc_uri
        self.is_saved = is_saved
        self._monitor = Monitor()
        self._on_finish = on_finish

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
                    self._monitor.check_cancelled()
                    self.lsp_messages.publish_diagnostics(doc_uri, found)
        except JsonRpcRequestCancelled:
            log.debug("Cancelled linting: %s.", self.doc_uri)

        except SubprocessDiedError:
            log.debug("Subprocess exited while linting: %s.", self.doc_uri)

        except Exception:
            log.exception("Error linting: %s.", self.doc_uri)

        finally:
            self._on_finish(self)

    def cancel(self):
        self._monitor.cancel()


def run_in_new_thread(func, thread_name):
    import threading

    t = threading.Thread(target=func)
    t.name = thread_name
    t.start()


class _LintManager(object):
    def __init__(self, server_manager, lsp_messages) -> None:
        import threading
        from robotframework_ls.server_manager import ServerManager

        self._server_manager: ServerManager = server_manager
        self._lsp_messages = lsp_messages

        self._next_id = partial(next, itertools.count())
        self._doc_id_to_info: Dict[str, _CurrLintInfo] = {}
        self._lock = threading.Lock()

    def schedule_lint(self, doc_uri: str, is_saved: bool, timeout: float) -> None:
        self.cancel_lint(doc_uri)
        rf_lint_api_client = self._server_manager.get_lint_rf_api_client(doc_uri)
        if rf_lint_api_client is None:
            log.info("Unable to get lint api for: %s", doc_uri)
            return

        lock = self._lock
        doc_id_to_info = self._doc_id_to_info

        def on_finish(curr_info: _CurrLintInfo):
            # When it's finished, remove it from our references (if it's still
            # the current one...).
            try:
                with lock:
                    if doc_id_to_info.get(curr_info.doc_uri) is curr_info:
                        del doc_id_to_info[curr_info.doc_uri]
            except:
                log.exception("Unhandled error on lint finish.")

        log.debug("Schedule lint for: %s", doc_uri)
        curr_info = _CurrLintInfo(
            rf_lint_api_client, self._lsp_messages, doc_uri, is_saved, on_finish
        )
        with self._lock:
            self._doc_id_to_info[doc_uri] = curr_info

        from robocorp_ls_core.timeouts import TimeoutTracker

        timeout_tracker = TimeoutTracker.get_singleton()
        timeout_tracker.call_on_timeout(
            timeout,
            partial(run_in_new_thread, curr_info, f"Lint: {doc_uri}"),
        )

    def cancel_lint(self, doc_uri: str) -> None:
        with self._lock:
            curr_info = self._doc_id_to_info.pop(doc_uri, None)
            if curr_info is not None:
                log.debug("Cancel lint for: %s", doc_uri)

                curr_info.cancel()


from robocorp_ls_core.command_dispatcher import _CommandDispatcher

command_dispatcher = _CommandDispatcher()


class RobotFrameworkLanguageServer(PythonLanguageServer):
    def __init__(self, rx, tx) -> None:
        from robocorp_ls_core.pluginmanager import PluginManager
        from robotframework_ls.rf_interactive_integration import _RfInterpretersManager
        from robotframework_ls.server_manager import ServerManager
        from robotframework_ls.ep_providers import DefaultConfigurationProvider
        from robotframework_ls.ep_providers import DefaultEndPointProvider
        from robotframework_ls.ep_providers import DefaultDirCacheProvider
        from robocorp_ls_core import watchdog_wrapper
        from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver
        from robocorp_ls_core.options import Setup
        from robotframework_ls.robotframework_ls_completion_impl import (
            _RobotFrameworkLsCompletionImpl,
        )

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
        self._rf_interpreters_manager = _RfInterpretersManager(self._endpoint, self._pm)

        watch_impl = os.environ.get("ROBOTFRAMEWORK_LS_WATCH_IMPL", "auto")
        if watch_impl not in ("watchdog", "fsnotify", "auto"):
            log.info(
                f"ROBOTFRAMEWORK_LS_WATCH_IMPL should be 'auto', 'watchdog' or 'fsnotify'. Found: {watch_impl} (falling back to auto)"
            )
            watch_impl = "auto"

        if watch_impl == "auto":
            # In auto mode we use watchdog for windows and fsnotify (polling)
            # for Linux and Mac. The reason for that is that on Linux and Mac
            # if big folders are watched the system may complain due to the
            # lack of resources, which may prevent the extension from working
            # properly.
            #
            # If users want to opt-in, they can change to watchdog (and
            # ideally install it to their env to get native extensions).
            if sys.platform == "win32":
                watch_impl = "watchdog"
            else:
                watch_impl = "fsnotify"

        log.info(
            "Using watch implementation: %s (customize with ROBOTFRAMEWORK_LS_WATCH_IMPL environment variable)",
            watch_impl,
        )

        self._fs_observer = watchdog_wrapper.create_remote_observer(
            watch_impl, (".py", ".libspec", "robot", ".resource")
        )
        remote_observer = typing.cast(RemoteFSObserver, self._fs_observer)

        log_file = Setup.options.log_file
        verbose = Setup.options.verbose
        if not isinstance(log_file, str) and log_file is not None:
            log.critical("Expected %r to be a str (was: %s)", log_file, type(log_file))
            log_file = None

        if not isinstance(verbose, int) and verbose is not None:
            log.critical("Expected %r to be an int (was: %s)", verbose, type(verbose))
            verbose = None

        remote_observer.start_server(log_file=log_file, verbose=verbose)

        self._server_manager = ServerManager(self._pm, language_server=self)
        self._lint_manager = _LintManager(self._server_manager, self._lsp_messages)
        self._robot_framework_ls_completion_impl = _RobotFrameworkLsCompletionImpl(
            self._server_manager, self
        )

    def get_remote_fs_observer_port(self) -> Optional[int]:
        from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver

        remote_observer = typing.cast(RemoteFSObserver, self._fs_observer)
        return remote_observer.port

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robotframework_ls.robot_config import RobotConfig

        return RobotConfig()

    @overrides(PythonLanguageServer._on_workspace_set)
    def _on_workspace_set(self, workspace: IWorkspace):
        PythonLanguageServer._on_workspace_set(self, workspace)
        self._server_manager.set_workspace(workspace)

    @overrides(PythonLanguageServer._obtain_fs_observer)
    def _obtain_fs_observer(self) -> IFSObserver:
        return self._fs_observer

    @overrides(PythonLanguageServer._create_workspace)
    def _create_workspace(
        self, root_uri: str, fs_observer: IFSObserver, workspace_folders
    ):
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        return RobotWorkspace(
            root_uri, fs_observer, workspace_folders, generate_ast=False
        )

    def m_initialize(
        self,
        processId=None,
        rootUri=None,
        rootPath=None,
        initializationOptions=None,
        workspaceFolders=None,
        **_kwargs,
    ) -> dict:
        # capabilities = _kwargs.get("capabilities", {})
        # text_document_capabilities = capabilities.get("textDocument", {})
        # document_symbol_capabilities = text_document_capabilities.get(
        #     "documentSymbol", {}
        # )
        # hierarchical_document_symbol_support = document_symbol_capabilities.get(
        #     "hierarchicalDocumentSymbolSupport", False
        # )
        # self._hierarchical_document_symbol_support = (
        #     hierarchical_document_symbol_support
        # )

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

    def forward_msg(self, msg: dict) -> None:
        method = msg["method"]
        self._endpoint.notify(method, msg["params"])

    @overrides(PythonLanguageServer.capabilities)
    def capabilities(self):
        from robocorp_ls_core.lsp import TextDocumentSyncKind
        from robotframework_ls.impl.semantic_tokens import TOKEN_TYPES, TOKEN_MODIFIERS
        from robotframework_ls import commands

        server_capabilities = {
            "codeActionProvider": False,
            "codeLensProvider": {"resolveProvider": True},
            "completionProvider": {"resolveProvider": True},  # Docs are lazily computed
            "documentFormattingProvider": True,
            "documentHighlightProvider": True,
            "documentRangeFormattingProvider": False,
            "documentSymbolProvider": True,
            "definitionProvider": True,
            "executeCommandProvider": {
                "commands": [
                    "robot.addPluginsDir",
                    "robot.resolveInterpreter",
                    "robot.getLanguageServerVersion",
                    "robot.getInternalInfo",
                    "robot.listTests",
                ]
                + commands.ALL_SERVER_COMMANDS
            },
            "hoverProvider": True,
            "referencesProvider": True,
            "renameProvider": False,
            "foldingRangeProvider": True,
            # Note that there are no auto-trigger characters (there's no good
            # character as there's no `(` for parameters and putting it as a
            # space becomes a bit too much).
            # Under review: added ' ' and '\t' now that we have info on the
            # active parameter (waiting for feedback from community here to
            # check whether this is good or annoying).
            "signatureHelpProvider": {"triggerCharacters": [" ", "\t"]},
            "textDocumentSync": {
                "change": TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
            "workspaceSymbolProvider": True,
            # The one below isn't accepted by lsp4j (it's still in LSP 3.15.0).
            # "workspaceSymbolProvider": {"workDoneProgress": False},
            "semanticTokensProvider": {
                "legend": {
                    "tokenTypes": TOKEN_TYPES,
                    "tokenModifiers": TOKEN_MODIFIERS,
                },
                "range": False,
                "full": True,
            },
        }
        log.debug("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_workspace__execute_command(self, command: str = "", arguments=()) -> Any:
        if command.startswith("robot.internal.rfinteractive."):
            return rf_interactive_integration.execute_command(
                command, self, self._rf_interpreters_manager, arguments
            )

        return command_dispatcher.dispatch(self, command, arguments)

    @command_dispatcher("robot.addPluginsDir")
    def _add_plugins_dir(self, *arguments):
        directory: str = arguments[0]
        assert os.path.isdir(directory), f"Expected: {directory} to be a directory."
        self._pm.load_plugins_from(Path(directory))
        return True

    @command_dispatcher(ROBOT_START_INDEXING_INTERNAL)
    def _start_indexing(self, *arguments):
        self._server_manager.get_regular_rf_api_client("")

    def m_robot__provide_evaluatable_expression(
        self, uri: str, position: PositionTypedDict
    ):
        rf_api_client = self._server_manager.get_others_api_client(uri)
        if rf_api_client is not None:
            func = partial(
                self._threaded_api_request,
                rf_api_client,
                "request_evaluatable_expression",
                doc_uri=uri,
                position=position,
            )
            func = require_monitor(func)
            return func

        log.info("Unable to provide evaluatable expression (no api available).")
        return None

    @command_dispatcher(ROBOT_WAIT_FULL_TEST_COLLECTION_INTERNAL)
    def _wait_for_full_test_collection(self, *arguments):
        rf_api_client = self._server_manager.get_regular_rf_api_client("")
        if rf_api_client is not None:
            func = partial(
                self._threaded_api_request_no_doc,
                rf_api_client,
                "request_wait_for_full_test_collection",
            )
            func = require_monitor(func)
            return func

        log.info("Unable to wait for first test collection (no api available).")
        return []

    @command_dispatcher("robot.getInternalInfo")
    def _get_internal_info(self, *arguments):
        in_memory_docs = []
        workspace = self.workspace
        if workspace:
            for doc in workspace.iter_documents():
                in_memory_docs.append({"uri": doc.uri})
        return {
            "settings": self.config.get_full_settings(),
            "inMemoryDocs": in_memory_docs,
            "processId": os.getpid(),
        }

    @command_dispatcher("robot.resolveInterpreter")
    def _resolve_interpreter(self, *arguments):
        try:
            from robocorp_ls_core import uris
            from robotframework_ls.ep_resolve_interpreter import (
                EPResolveInterpreter,
            )
            from robotframework_ls.ep_resolve_interpreter import IInterpreterInfo

            target_robot = arguments[0]

            if isinstance(target_robot, (list, tuple)):
                if len(target_robot) > 0:
                    target_robot = target_robot[0]

            robot_uri = uris.from_fs_path(target_robot)

            for ep in self._pm.get_implementations(EPResolveInterpreter):
                interpreter_info: IInterpreterInfo = (
                    ep.get_interpreter_info_for_doc_uri(robot_uri)
                )
                if interpreter_info is not None:
                    return {
                        "pythonExe": interpreter_info.get_python_exe(),
                        "environ": interpreter_info.get_environ(),
                        "additionalPythonpathEntries": interpreter_info.get_additional_pythonpath_entries(),
                    }
        except:
            log.exception(f"Error resolving interpreter. Args: {arguments}")

    @command_dispatcher("robot.getLanguageServerVersion")
    def _get_language_server_version(self, *arguments):
        return __version__

    @command_dispatcher(ROBOT_GET_RFLS_HOME_DIR)
    def _get_rfls_home_dir(self, *arguments):
        from robotframework_ls import robot_config

        return robot_config.get_robotframework_ls_home()

    @command_dispatcher("robot.listTests")
    def _list_tests(self, *arguments):
        doc_uri = arguments[0]["uri"]

        rf_api_client = self._server_manager.get_others_api_client(doc_uri)
        if rf_api_client is not None:
            func = partial(
                self._threaded_api_request,
                rf_api_client,
                "request_list_tests",
                doc_uri=doc_uri,
            )
            func = require_monitor(func)
            return func

        log.info("Unable to list tests (no api available).")
        return []

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    @log_and_silence_errors(log)
    def m_workspace__did_change_configuration(self, **kwargs):
        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        self._server_manager.set_config(self.config)

    # --- Methods to forward to the api

    @overrides(PythonLanguageServer.m_shutdown)
    @log_and_silence_errors(log)
    def m_shutdown(self, **kwargs):
        try:
            from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver

            remote_observer = typing.cast(RemoteFSObserver, self._fs_observer)
            remote_observer.dispose()
        except Exception:
            log.exception("Error disposing RemoteFSObserver.")
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
        doc_uri = textDocument["uri"]

        source_format_rf_api_client = self._server_manager.get_others_api_client(
            doc_uri
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
            ("api", "lint", "others"),
            "textDocument/didClose",
            {"textDocument": textDocument},
        )
        PythonLanguageServer.m_text_document__did_close(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_open)
    def m_text_document__did_open(self, textDocument=None, **_kwargs):
        self._server_manager.forward(
            ("api", "lint", "others"),
            "textDocument/didOpen",
            {"textDocument": textDocument},
        )
        PythonLanguageServer.m_text_document__did_open(
            self, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_text_document__did_change)
    def m_text_document__did_change(
        self, contentChanges=None, textDocument=None, **_kwargs
    ):
        self._server_manager.forward(
            ("api", "lint", "others"),
            "textDocument/didChange",
            {"contentChanges": contentChanges, "textDocument": textDocument},
        )
        PythonLanguageServer.m_text_document__did_change(
            self, contentChanges=contentChanges, textDocument=textDocument, **_kwargs
        )

    @overrides(PythonLanguageServer.m_workspace__did_change_workspace_folders)
    def m_workspace__did_change_workspace_folders(self, event=None, **_kwargs):
        self._server_manager.forward(
            ("api", "lint", "others"),
            "workspace/didChangeWorkspaceFolders",
            {"event": event},
        )
        PythonLanguageServer.m_workspace__did_change_workspace_folders(
            self, event=event, **_kwargs
        )

    # --- Customized implementation

    @overrides(PythonLanguageServer.lint)
    def lint(self, doc_uri, is_saved, content_changes=None) -> None:
        # We want the timeout to be shorter if it was saved or if the user
        # typed a new line.
        timeout = _LINT_DEBOUNCE_IN_SECONDS_LOW
        if not is_saved:
            timeout = _LINT_DEBOUNCE_IN_SECONDS_HIGH
            for change in content_changes:
                try:
                    text = change.get("text", "")
                    if "\n" in text or "\r" in text:
                        timeout = _LINT_DEBOUNCE_IN_SECONDS_LOW
                        break
                except:
                    log.exception(
                        "Error computing lint timeout with: %s", content_changes
                    )
        self._lint_manager.schedule_lint(doc_uri, is_saved, timeout)

    @overrides(PythonLanguageServer.cancel_lint)
    def cancel_lint(self, doc_uri) -> None:
        self._lint_manager.cancel_lint(doc_uri)

    def m_completion_item__resolve(self, **params):
        completion_item: CompletionItemTypedDict = params
        return self._robot_framework_ls_completion_impl.resolve_completion_item(
            completion_item
        )

    def m_text_document__completion(self, **params):
        doc_uri = params["textDocument"]["uri"]
        # Note: 0-based
        line, col = params["position"]["line"], params["position"]["character"]
        return self._robot_framework_ls_completion_impl.text_document_completion(
            doc_uri, line, col
        )

    @log_and_silence_errors(log)
    def _threaded_api_request(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        request_method_name: str,
        doc_uri: str,
        monitor: IMonitor,
        __timeout__=DEFAULT_COMPLETIONS_TIMEOUT,
        __log__=False,
        **kwargs,
    ):
        from robocorp_ls_core.client_base import wait_for_message_matcher

        func = getattr(rf_api_client, request_method_name)

        ws = self.workspace
        if not ws:
            log.critical(
                "Workspace must be set before calling %s.", request_method_name
            )
            return None

        document = ws.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.critical(
                "Unable to find document (%s) for %s." % (doc_uri, request_method_name)
            )
            return None

        # Asynchronous completion.
        message_matcher: Optional[IIdMessageMatcher] = func(doc_uri, **kwargs)
        if message_matcher is None:
            log.debug("Message matcher for %s returned None.", request_method_name)
            return None

        if wait_for_message_matcher(
            message_matcher,
            rf_api_client.request_cancel,
            __timeout__,
            monitor,
        ):
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if __log__:
                    log.info("Result: %s", result)
                if result:
                    return result

        return None

    @log_and_silence_errors(log)
    def _threaded_api_request_no_doc(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        request_method_name: str,
        monitor: Optional[IMonitor],
        **kwargs,
    ):
        from robocorp_ls_core.client_base import wait_for_message_matcher

        func = getattr(rf_api_client, request_method_name)

        # Asynchronous completion.
        message_matcher: Optional[IIdMessageMatcher] = func(**kwargs)
        if message_matcher is None:
            log.debug("Message matcher for %s returned None.", request_method_name)
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

    def async_api_forward(
        self,
        api_client_method_name,
        target_api,
        doc_uri,
        default_return=None,
        __add_doc_uri_in_args__=True,
        **kwargs,
    ):
        rf_api_client: IRobotFrameworkApiClient
        if target_api == "api":
            rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        elif target_api == "lint":
            rf_api_client = self._server_manager.get_lint_rf_api_client(doc_uri)
        elif target_api == "others":
            rf_api_client = self._server_manager.get_others_api_client(doc_uri)
        else:
            raise AssertionError(f"Unexpected: {target_api}")
        if rf_api_client is not None:
            if __add_doc_uri_in_args__:
                func = partial(
                    self._threaded_api_request,
                    rf_api_client,
                    api_client_method_name,
                    doc_uri=doc_uri,
                    **kwargs,
                )
            else:
                func = partial(
                    self._threaded_api_request_no_doc,
                    rf_api_client,
                    api_client_method_name,
                    **kwargs,
                )
            func = require_monitor(func)
            return func

        log.info(
            "No api available (call: %s, uri: %s).", api_client_method_name, doc_uri
        )
        return default_return

    def m_text_document__definition(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]
        return self.async_api_forward(
            "request_find_definition", "api", doc_uri, line=line, col=col
        )

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

        return self.async_api_forward(
            "request_signature_help", "api", doc_uri, line=line, col=col
        )

    def m_text_document__folding_range(self, **kwargs):
        """
        "params": {
            "textDocument": {
                "uri": "file:///x%3A/vscode-robot/local_test/Basic/resources/keywords.robot"
            },
        },
        """
        doc_uri = kwargs["textDocument"]["uri"]

        return self.async_api_forward("request_folding_range", "others", doc_uri)

    def m_text_document__code_lens(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        return self.async_api_forward("request_code_lens", "others", doc_uri)

    def m_code_lens__resolve(self, **kwargs):
        code_lens: CodeLensTypedDict = kwargs

        code_lens_command = code_lens.get("command")
        data = code_lens.get("data")
        if code_lens_command is None and isinstance(data, dict):
            # For the interactive shell we need to resolve the arguments.
            doc_uri = data.get("uri")

            return self.async_api_forward(
                "request_resolve_code_lens",
                "others",
                doc_uri,
                code_lens=code_lens,
                __add_doc_uri_in_args__=False,
            )

        return code_lens

    def m_text_document__document_symbol(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        return self.async_api_forward("request_document_symbol", "others", doc_uri)

    def m_text_document__hover(self, **kwargs):
        params: TextDocumentPositionParamsTypedDict = kwargs
        doc_uri = params["textDocument"]["uri"]
        # Note: 0-based
        line, col = params["position"]["line"], params["position"]["character"]

        return self.async_api_forward(
            "request_hover", "api", doc_uri, line=line, col=col
        )

    def m_text_document__references(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]
        include_declaration = kwargs["context"]["includeDeclaration"]

        # Note: we want to use the same one used by m_workspace__symbol (to reuse
        # the related caches).
        rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        if rf_api_client is not None:
            func = partial(
                self._threaded_api_request,
                rf_api_client,
                "request_references",
                doc_uri=doc_uri,
                line=line,
                col=col,
                include_declaration=include_declaration,
                __timeout__=9999999,
            )
            func = require_monitor(func)
            return func

        log.info("Unable to compute references (no api available).")
        return []

    def m_text_document__semantic_tokens__range(self, textDocument=None, range=None):
        raise RuntimeError("Not currently implemented!")

    def m_text_document__semantic_tokens__full(self, textDocument=None):
        doc_uri = textDocument["uri"]
        api = self._server_manager.get_others_api_client(doc_uri)
        if api is None:
            log.info("Unable to get api client when computing semantic tokens (full).")
            return {"resultId": None, "data": []}

        func = partial(
            self._threaded_api_request_no_doc,
            api,
            "request_semantic_tokens_full",
            text_document=textDocument,
        )
        func = require_monitor(func)
        return func

    def m_workspace__symbol(self, query: Optional[str] = None) -> Any:
        api = self._server_manager.get_regular_rf_api_client("")
        if api is None:
            log.info("Unable to search workspace symbols (no api available).")
            return None

        func = partial(
            self._threaded_api_request_no_doc,
            api,
            "request_workspace_symbols",
            query=query,
        )
        func = require_monitor(func)
        return func

    def m_text_document__document_highlight(self, **kwargs):
        params: TextDocumentPositionParamsTypedDict = kwargs
        doc_uri = params["textDocument"]["uri"]
        line, col = params["position"]["line"], params["position"]["character"]
        api = self._server_manager.get_others_api_client(doc_uri)
        if api is None:
            log.info("Unable to get api client when computing document highlight.")
            return None

        func = partial(
            self._threaded_api_request,
            api,
            "request_document_highlight",
            doc_uri=doc_uri,
            line=line,
            col=col,
        )
        func = require_monitor(func)
        return func
