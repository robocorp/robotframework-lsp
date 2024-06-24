import json
import tempfile
from robocorp_ls_core.command_dispatcher import _CommandDispatcher
from robocorp_ls_core.python_ls import (
    PythonLanguageServer,
    BaseLintManager,
    BaseLintInfo,
)
from robocorp_ls_core.basic import (
    overrides,
    log_and_silence_errors,
    log_but_dont_silence_errors,
)
import os
import time
from robocorp_ls_core.robotframework_log import get_logger
from typing import Any, Optional, Dict, Union
from robocorp_ls_core.protocols import (
    IConfig,
    IWorkspace,
    IIdMessageMatcher,
    IRobotFrameworkApiClient,
    IMonitor,
    IEndPoint,
    ActionResultDict,
    IFuture,
    Sentinel,
)
from pathlib import Path
from robotframework_ls.ep_providers import (
    EPConfigurationProvider,
    EPDirCacheProvider,
    EPEndPointProvider,
)
from robocorp_ls_core.jsonrpc.endpoint import require_monitor
from functools import partial
from robotframework_ls import __version__, rf_interactive_integration
import typing
import sys
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from robocorp_ls_core.lsp import (
    CodeLensTypedDict,
    TextDocumentPositionParamsTypedDict,
    PositionTypedDict,
    CompletionItemTypedDict,
    RenameParamsTypedDict,
    PrepareRenameParamsTypedDict,
    SelectionRangeParamsTypedDict,
    TextDocumentCodeActionTypedDict,
    WorkspaceEditParamsTypedDict,
    ShowDocumentParamsTypedDict,
)
from robotframework_ls.commands import (
    ROBOT_GET_RFLS_HOME_DIR,
    ROBOT_OPEN_FLOW_EXPLORER_INTERNAL,
    ROBOT_START_INDEXING_INTERNAL,
    ROBOT_WAIT_FULL_TEST_COLLECTION_INTERNAL,
    ROBOT_RF_INFO_INTERNAL,
    ROBOT_LINT_WORKSPACE,
    ROBOT_LINT_EXPLORER,
    ROBOT_GENERATE_FLOW_EXPLORER_MODEL,
    ROBOT_COLLECT_ROBOT_DOCUMENTATION,
    ROBOT_CONVERT_OUTPUT_XML_TO_ROBOSTREAM,
    ROBOT_APPLY_CODE_ACTION,
)
from robocorp_ls_core.jsonrpc.exceptions import JsonRpcException
import weakref
from io import StringIO


log = get_logger(__name__)


command_dispatcher = _CommandDispatcher()


class _CurrLintInfo(BaseLintInfo):
    def __init__(
        self,
        rf_lint_api_client: IRobotFrameworkApiClient,
        lsp_messages,
        doc_uri,
        is_saved,
        weak_lint_manager,
    ) -> None:
        self._rf_lint_api_client = rf_lint_api_client
        BaseLintInfo.__init__(self, lsp_messages, doc_uri, is_saved, weak_lint_manager)

    @overrides(BaseLintInfo._do_lint)
    def _do_lint(self):
        from robotframework_ls.server_api.client import SubprocessDiedError

        try:
            from robocorp_ls_core.client_base import wait_for_message_matcher

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
        except SubprocessDiedError:
            log.debug("Subprocess exited while linting: %s.", self.doc_uri)


class _LintManager(BaseLintManager):
    def __init__(
        self, server_manager, lsp_messages, endpoint: IEndPoint, read_queue
    ) -> None:
        from robotframework_ls.server_manager import ServerManager

        self._server_manager: ServerManager = server_manager
        BaseLintManager.__init__(self, lsp_messages, endpoint, read_queue)

    @overrides(BaseLintManager._create_curr_lint_info)
    def _create_curr_lint_info(
        self, doc_uri: str, is_saved: bool, timeout: float
    ) -> Optional[BaseLintInfo]:
        # Note: this call must be done in the main thread.
        rf_lint_api_client = self._server_manager.get_lint_rf_api_client(doc_uri)
        if rf_lint_api_client is None:
            log.info("Unable to get lint api for: %s", doc_uri)
            return None

        weak_lint_manager = weakref.ref(self)

        log.debug("Schedule lint for: %s", doc_uri)
        curr_info = _CurrLintInfo(
            rf_lint_api_client, self._lsp_messages, doc_uri, is_saved, weak_lint_manager
        )
        return curr_info


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

        self._last_doc_uri: str = ""
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

        weak_self = weakref.ref(self)

        def get_workspace_root_path():
            s = weak_self()  # We don't want a cyclic reference.
            if s is None:
                return None
            ws = s.workspace
            if ws is not None:
                return ws.root_path
            return None

        # Either 'none', 'robocorp' or 'sema4ai'.
        self._integration_option = "none"

        def get_integration_option():
            s = weak_self()  # We don't want a cyclic reference.
            if s is None:
                return "none"
            return s._integration_option

        self._rf_interpreters_manager = _RfInterpretersManager(
            self._endpoint,
            self._pm,
            get_workspace_root_path=get_workspace_root_path,
            get_integration_option=get_integration_option,
        )

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
        self._robot_framework_ls_completion_impl = _RobotFrameworkLsCompletionImpl(
            self._server_manager, self
        )

    @overrides(PythonLanguageServer._create_lint_manager)
    def _create_lint_manager(self) -> BaseLintManager:
        return _LintManager(
            self._server_manager,
            self._lsp_messages,
            self._endpoint,
            self._jsonrpc_stream_reader.get_read_queue(),
        )

    def _execute_on_main_thread(self, on_main_thread_callback):
        read_queue = self._jsonrpc_stream_reader.get_read_queue()
        read_queue.put(on_main_thread_callback)

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

        initialization_options = initializationOptions
        if initialization_options:
            integration_option = initialization_options.get("integrationOption", "none")
            # Integration may be "none", "sema4ai" or "robocorp"
            self._integration_option = integration_option

        ret = PythonLanguageServer.m_initialize(
            self,
            processId=processId,
            rootUri=rootUri,
            rootPath=rootPath,
            initializationOptions=initializationOptions,
            workspaceFolders=workspaceFolders,
            **_kwargs,
        )

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
            "codeActionProvider": {
                "resolveProvider": False,
                "codeActionKinds": [
                    "quickfix",
                    "refactor",
                    "refactor.extract.local",
                    "assign.toVar",
                    "surroundWith.tryExcept",
                    "surroundWith.tryExceptFinally",
                ],
            },
            "codeLensProvider": {"resolveProvider": True},
            # Docs are lazily computed
            "completionProvider": {"resolveProvider": True},
            "documentFormattingProvider": True,
            "documentHighlightProvider": True,
            "documentRangeFormattingProvider": False,
            # Note: infrastructure for onTypeFormatting is in place but we don't
            # really do anything with it, so, don't specify it now.
            # "documentOnTypeFormattingProvider": {
            #     "firstTriggerCharacter": "\n",
            #     "moreTriggerCharacter": ["\r"],
            # },
            "documentSymbolProvider": True,
            "definitionProvider": True,
            "selectionRangeProvider": True,
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
            "renameProvider": {
                "prepareProvider": True,
            },
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

    @command_dispatcher(ROBOT_COLLECT_ROBOT_DOCUMENTATION)
    def _collect_robot_documentation(
        self, opts
    ) -> Union[ActionResultDict, "partial[Any]"]:
        from robotframework_ls.ls_timeouts import get_timeout
        from robotframework_ls.ls_timeouts import TimeoutReason

        uri = opts.get("uri")
        if not uri:
            return dict(success=False, message="uri not provided", result=None)

        # We can either accept uri/library name or uri/line/col.
        # If both are provided the library_name is preferred.
        library_name = opts.get("library_name")
        line = opts.get("line")
        col = opts.get("col")
        if not library_name:
            if line is None or col is None:
                return dict(
                    success=False,
                    message="Either library_name or line/col must be provided.",
                    result=None,
                )

        rf_api_client = self._server_manager.get_others_api_client(uri)
        if rf_api_client is not None:
            timeout = get_timeout(self.config, TimeoutReason.collect_docs_timeout)
            func = partial(
                self._threaded_api_request_no_doc,
                rf_api_client,
                "request_collect_robot_documentation",
                __timeout__=timeout,
                doc_uri=uri,
                library_name=library_name,
                line=line,
                col=col,
            )
            func = require_monitor(func)
            return func

        return dict(success=False, message="no api available", result=None)

    @command_dispatcher(ROBOT_START_INDEXING_INTERNAL)
    def _start_indexing(self, *arguments):
        self._server_manager.get_regular_rf_api_client("")

    @command_dispatcher(ROBOT_LINT_WORKSPACE)
    def _lint_workspace(self, *arguments):
        folder_paths = self.workspace.get_folder_paths()
        self._lint_manager.schedule_manual_lint(folder_paths)

    @command_dispatcher(ROBOT_LINT_EXPLORER)
    def _lint_explorer(self, current_item, selection=None):
        if not selection:
            log.critical("The selection must be given for %s", ROBOT_LINT_EXPLORER)
            return

        if not isinstance(selection, (list, tuple)):
            log.critical(
                "The selection must be a list or tuple for %s. Found: %r",
                ROBOT_LINT_EXPLORER,
                selection,
            )
            return

        paths_to_analyze = set()
        for item in selection:
            if not isinstance(item, dict):
                log.critical(
                    "Expected item to be a dict for %s. Found: %r",
                    ROBOT_LINT_EXPLORER,
                    item,
                )
                continue

            fs_path = item.get("fsPath")
            if not fs_path:
                fs_path = item.get("path")
                if not fs_path:
                    log.critical(
                        "Expected item to be a dict with fsPath or path for %s. Found: %r",
                        ROBOT_LINT_EXPLORER,
                        item,
                    )
                    continue

            paths_to_analyze.add(fs_path)
        self._lint_manager.schedule_manual_lint(paths_to_analyze)

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

    @command_dispatcher(ROBOT_CONVERT_OUTPUT_XML_TO_ROBOSTREAM)
    def _convert_output_xml_to_rfstream(self, opts: Dict[str, Any]):
        def convert_in_thread():
            from robotframework_ls import import_robot_out_stream

            import_robot_out_stream()

            from robot_out_stream import xml_to_rfstream

            source = opts.get("xml_path")
            if source:
                with tempfile.NamedTemporaryFile(
                    "w", suffix=".robostream", delete=False
                ) as temp:

                    def write(contents):
                        temp.write(contents)

                    xml_to_rfstream.convert_xml_to_rfstream(source, write)

                # Note that we just send the temp file if an input file was received
                # (usually this should only happen if it's too big).
                # The client is responsible for deleting it after using it.
                return temp.name

            # We received contents (return contents too).
            xml_contents = opts.get("xml_contents")
            if xml_contents is None:
                raise RuntimeError(
                    f"Expected either xml_path or xml_contents. Keys: {list(opts.keys())}"
                )

            source = StringIO()
            source.write(xml_contents)
            source.seek(0)

            full_contents = []

            def write2(contents):
                full_contents.append(contents)

            xml_to_rfstream.convert_xml_to_rfstream(source, write2)
            return "".join(full_contents)

        return convert_in_thread

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

    @command_dispatcher(ROBOT_RF_INFO_INTERNAL)
    def _get_rf_info_internal(self, *arguments):
        doc_uri = arguments[0]["uri"]

        api = self._server_manager._get_others_api(doc_uri)
        if api is not None:
            info = api.get_interpreter_info()
            rf_api_client = api.get_robotframework_api_client()
            if rf_api_client is not None:

                def func(monitor):
                    ret = self._threaded_api_request(
                        rf_api_client,
                        "request_rf_info",
                        doc_uri=doc_uri,
                        monitor=monitor,
                    )
                    if info is not None:
                        if isinstance(ret, dict):
                            ret["interpreter_id"] = info.get_interpreter_id()
                    return ret

                func = require_monitor(func)
                return func

        log.info("Unable to get RF info (no api available).")
        return None

    @command_dispatcher(ROBOT_GENERATE_FLOW_EXPLORER_MODEL)
    def _generate_flow_explorer_model(self, opts: Dict[str, Any]):
        """
        :param opts:
            A dictionary with the options to generate the flow explorer model.
            Options available:
                - uri: target uri mapping to the robot or directory with multiple
                  robots from where the model should be generated.

        """
        uri = opts["uri"]

        return self.async_api_forward("request_flow_explorer_model", "api", doc_uri=uri)

    @command_dispatcher(ROBOT_OPEN_FLOW_EXPLORER_INTERNAL)
    def _open_flow_explorer(self, opts) -> ActionResultDict:
        """
        :param dict opts:
            Keys:
                "currentFileUri": uri for target (may also be folder).
                "htmlBundleFolderPath":folder which contains the html/js assets.
        """
        from robotframework_ls.constants import (
            DEFAULT_ROBOT_FLOW_EXPLORER_HTML_TEMPLATE,
            DEFAULT_ROBOT_FLOW_EXPLORER_OPTIONS,
        )
        from robocorp_ls_core.uris import from_fs_path
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_FLOW_EXPLORER_THEME_DARK,
        )
        from robotframework_ls.impl.robot_generated_lsp_constants import (
            OPTION_ROBOT_FLOW_EXPLORER_THEME,
        )

        current_doc_uri = opts["currentFileUri"]
        html_bundle_flow_folder_path = opts["htmlBundleFolderPath"]
        log.info(
            "Dispatched flow explorer internal command with args:",
            str(current_doc_uri),
            str(html_bundle_flow_folder_path),
        )

        def finish_and_convert_result(result: ActionResultDict) -> ActionResultDict:
            log.info("Generating web page for visualization...")

            if not result["success"]:
                return result

            # identify the selected theme & construct options
            rfe_theme = self._config.get_setting(
                OPTION_ROBOT_FLOW_EXPLORER_THEME,
                str,
                OPTION_ROBOT_FLOW_EXPLORER_THEME_DARK,
            )
            rfe_options = DEFAULT_ROBOT_FLOW_EXPLORER_OPTIONS.copy()
            rfe_options["theme"] = rfe_theme
            model = result["result"]

            # filling in the HTML template
            # adding the new model as data to Flow Explorer
            replacement_html = DEFAULT_ROBOT_FLOW_EXPLORER_HTML_TEMPLATE.substitute(
                rfe_options=json.dumps(rfe_options),
                rfe_data=json.dumps(model),
                rfe_favicon_path=Path(
                    os.path.join(html_bundle_flow_folder_path, "favicon.png")
                ).as_uri(),
                rfe_js_path=Path(
                    os.path.join(
                        html_bundle_flow_folder_path, "robot_flow_explorer_bundle.js"
                    )
                ).as_uri(),
            )
            # create the temporary HTML file to display
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html"
            ) as temp_file:
                Path(temp_file.name).write_text(replacement_html, encoding="utf-8")
                return {
                    "result": from_fs_path(temp_file.name),
                    "success": True,
                    "message": None,
                }

        return self.async_api_forward(
            "request_flow_explorer_model",
            "api",
            doc_uri=current_doc_uri,
            uri=current_doc_uri,
            __add_doc_uri_in_args__=False,
            __convert_result__=finish_and_convert_result,
            __timeout__=999999,  # No timeout for the flow explorer...
        )

    @command_dispatcher("robot.listTests")
    def _list_tests(self, *arguments):
        from robotframework_ls.ls_timeouts import get_timeout
        from robotframework_ls.ls_timeouts import TimeoutReason

        doc_uri = arguments[0]["uri"]

        rf_api_client = self._server_manager.get_others_api_client(doc_uri)
        if rf_api_client is not None:
            timeout = get_timeout(self.config, TimeoutReason.list_tests_timeout)
            func = partial(
                self._threaded_api_request_no_doc,
                rf_api_client,
                "request_list_tests",
                doc_uri=doc_uri,
                __timeout__=timeout,
            )
            func = require_monitor(func)
            return func

        log.info("Unable to list tests (no api available).")
        return []

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    @log_and_silence_errors(log)
    def m_workspace__did_change_configuration(self, **kwargs) -> None:
        from robotframework_ls.impl import robot_localization

        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        robot_localization.set_global_from_config(self.config)
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
        from robotframework_ls.ls_timeouts import get_timeout
        from robotframework_ls.ls_timeouts import TimeoutReason

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
        config = self.config
        maxtime = curtime + get_timeout(config, TimeoutReason.code_formatting)

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

    @log_but_dont_silence_errors(log)
    def _threaded_api_request(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        request_method_name: str,
        doc_uri: str,
        monitor: IMonitor,
        __timeout__=Sentinel.USE_DEFAULT_TIMEOUT,
        __log__=False,
        __convert_result__=None,
        **kwargs,
    ):
        from robocorp_ls_core.client_base import wait_for_message_matcher
        from robotframework_ls.ls_timeouts import get_timeout
        from robotframework_ls.ls_timeouts import TimeoutReason

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

        __timeout__ = get_timeout(self.config, TimeoutReason.general, __timeout__)
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
                    if __convert_result__ is not None:
                        result = __convert_result__(result)
                    return result

                error = msg.get("error")
                if error:
                    raise JsonRpcException(**error)

        return None

    @log_but_dont_silence_errors(log)
    def _threaded_api_request_no_doc(
        self,
        rf_api_client: IRobotFrameworkApiClient,
        request_method_name: str,
        monitor: Optional[IMonitor],
        __timeout__=Sentinel.USE_DEFAULT_TIMEOUT,
        __convert_result__=None,
        **kwargs,
    ):
        from robocorp_ls_core.client_base import wait_for_message_matcher
        from robotframework_ls.ls_timeouts import TimeoutReason
        from robotframework_ls.ls_timeouts import get_timeout

        func = getattr(rf_api_client, request_method_name)

        # Asynchronous completion.
        message_matcher: Optional[IIdMessageMatcher] = func(**kwargs)
        if message_matcher is None:
            log.debug("Message matcher for %s returned None.", request_method_name)
            return None

        __timeout__ = get_timeout(self.config, TimeoutReason.general, __timeout__)

        if wait_for_message_matcher(
            message_matcher,
            rf_api_client.request_cancel,
            __timeout__,
            monitor,
        ):
            msg = message_matcher.msg
            if msg is not None:
                result = msg.get("result")
                if result:
                    if __convert_result__ is not None:
                        result = __convert_result__(result)
                    return result

        return None

    def async_api_forward(
        self,
        api_client_method_name: str,
        target_api: str,  # api, lint, others
        doc_uri: str,
        default_return=None,
        __add_doc_uri_in_args__=True,
        **kwargs,
    ):
        rf_api_client: Optional[IRobotFrameworkApiClient]
        if target_api == "api":
            rf_api_client = self._server_manager.get_regular_rf_api_client(doc_uri)
        elif target_api == "lint":
            rf_api_client = self._server_manager.get_lint_rf_api_client(doc_uri)
        elif target_api == "others":
            rf_api_client = self._server_manager.get_others_api_client(doc_uri)
        else:
            raise AssertionError(f"Unexpected: {target_api}")

        self._last_doc_uri = doc_uri
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

    def m_text_document__rename(self, **kwargs):
        rename_params: RenameParamsTypedDict = kwargs
        # Note: 0-based
        doc_uri: str = rename_params["textDocument"]["uri"]
        line: int = rename_params["position"]["line"]
        col: int = rename_params["position"]["character"]
        new_name = rename_params["newName"]
        return self.async_api_forward(
            "request_rename", "api", doc_uri, line=line, col=col, new_name=new_name
        )

    def m_text_document__prepare_rename(self, **kwargs):
        rename_params: PrepareRenameParamsTypedDict = kwargs
        # Note: 0-based
        doc_uri: str = rename_params["textDocument"]["uri"]
        line: int = rename_params["position"]["line"]
        col: int = rename_params["position"]["character"]
        return self.async_api_forward(
            "request_prepare_rename", "api", doc_uri, line=line, col=col
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

    def m_text_document__on_type_formatting(self, **kwargs):
        doc_uri = kwargs["textDocument"]["uri"]

        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        ch = kwargs["ch"]
        return self.async_api_forward(
            "request_on_type_formatting", "others", doc_uri, ch=ch, line=line, col=col
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

    def m_text_document__selection_range(self, **kwargs):
        params: SelectionRangeParamsTypedDict = kwargs
        # Note: 0-based
        doc_uri: str = params["textDocument"]["uri"]
        positions = params["positions"]
        return self.async_api_forward(
            "request_selection_range", "others", doc_uri, positions=positions
        )

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

        return self.async_api_forward(
            "request_semantic_tokens_full",
            "others",
            doc_uri,
            default_return={"resultId": None, "data": []},
            text_document=textDocument,
            __add_doc_uri_in_args__=False,
        )

    def m_workspace__symbol(self, query: Optional[str] = None) -> Any:
        doc_uri = self._last_doc_uri
        return self.async_api_forward(
            "request_workspace_symbols",
            "api",
            doc_uri,
            query=query,
            __add_doc_uri_in_args__=False,
        )

    def m_text_document__document_highlight(self, **kwargs):
        params: TextDocumentPositionParamsTypedDict = kwargs
        doc_uri = params["textDocument"]["uri"]
        line, col = params["position"]["line"], params["position"]["character"]

        return self.async_api_forward(
            "request_document_highlight", "others", doc_uri, line=line, col=col
        )

    def m_cancel_progress(self, progressId):
        if not PythonLanguageServer.m_cancel_progress(self, progressId=progressId):
            for api in self._server_manager.collect_apis():
                # We don't keep track of which server started which progress,
                # so, we send it to all the APIs.
                api.forward_async("cancelProgress", {"progressId": progressId})
        return True

    def m_text_document__code_action(self, **kwargs):
        params: TextDocumentCodeActionTypedDict = kwargs
        # Sample params:
        # {
        #     "textDocument": {
        #         "uri": "file:///x%3A/vscode-robot/local_test/robot_check/checkmy.robot"
        #     },
        #     "range": {
        #         "start": {"line": 12, "character": 5},
        #         "end": {"line": 12, "character": 5},
        #     },
        #     "context": {
        #         "diagnostics": [
        #             {
        #                 "range": {
        #                     "start": {"line": 12, "character": 4},
        #                     "end": {"line": 12, "character": 8},
        #                 },
        #                 "message": "Undefined keyword: rara.",
        #                 "severity": 1,
        #                 "source": "robotframework",
        #             }
        #         ],
        #         "triggerKind": 1,
        #     },
        # }
        doc_uri = params["textDocument"]["uri"]
        # Note: we have to use the "api" server which has symbols caches.
        return self.async_api_forward(
            "request_code_action", "api", doc_uri, params=params
        )

    @command_dispatcher(ROBOT_APPLY_CODE_ACTION)
    def _apply_code_action(self, code_action_info):
        weak_self = weakref.ref(self)

        def in_thread(*args, **kwargs):
            self = weak_self()
            if self is None:
                return

            apply_edit: Optional[WorkspaceEditParamsTypedDict] = code_action_info.get(
                "apply_edit"
            )
            if apply_edit:
                fut: IFuture = self._lsp_messages.apply_edit_args(apply_edit)
                try:
                    fut.result(4)
                except:
                    log.exception(
                        f"Exception calling: {self._lsp_messages.M_APPLY_EDIT}"
                    )

            apply_snippet: Optional[
                WorkspaceEditParamsTypedDict
            ] = code_action_info.get("apply_snippet")
            if apply_snippet:
                fut: IFuture = self._lsp_messages.apply_snippet(apply_snippet)
                try:
                    fut.result(4)
                except:
                    log.exception(
                        f"Exception calling: {self._lsp_messages.M_APPLY_SNIPPET}"
                    )

            # Deal with linting (because if only a dependent file is changed we
            # still want to ask for the main file to be linted).
            lint_uris = code_action_info.get("lint_uris")
            if lint_uris:
                for uri in lint_uris:
                    self._execute_on_main_thread(partial(self.lint, uri, is_saved=True))

            # Force showing some document?
            show_document_args: Optional[
                ShowDocumentParamsTypedDict
            ] = code_action_info.get("show_document")
            log.info("Show document: %s", show_document_args)
            self._lsp_messages.show_document(show_document_args)

        return in_thread
