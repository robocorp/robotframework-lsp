from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.basic import overrides, log_and_silence_errors
import os
import time
from robotframework_ls.constants import DEFAULT_COMPLETIONS_TIMEOUT
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core import basic
from typing import Any, Optional
from robocorp_ls_core.protocols import IMessageMatcher, IConfig, IWorkspace
from pathlib import Path
from robotframework_ls.ep_providers import (
    EPConfigurationProvider,
    EPDirCacheProvider,
    EPEndPointProvider,
)


log = get_logger(__name__)

LINT_DEBOUNCE_S = 0.5  # 500 ms


class RobotFrameworkLanguageServer(PythonLanguageServer):
    def __init__(self, rx, tx):
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
            # "signatureHelpProvider": {
            #     'triggerCharacters': ['(', ',', '=']
            # },
            "textDocumentSync": {
                "change": TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": False},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
        }
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

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
        source_format_api = self._server_manager.get_source_format_api()
        message_matcher = source_format_api.request_source_format(
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
    @basic.debounce(LINT_DEBOUNCE_S, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved) -> None:
        # Since we're debounced, the document may no longer be open
        try:
            lint_api = self._server_manager.get_lint_api(doc_uri)
            found = []
            diagnostics_msg = lint_api.lint(doc_uri)
            if diagnostics_msg:
                found = diagnostics_msg.get("result", [])
            self._lsp_messages.publish_diagnostics(doc_uri, found)
        except Exception:
            # Because it's debounced, we can't use the log_and_silence_errors decorator.
            log.exception("Error linting.")

    def m_text_document__definition(self, **kwargs) -> Optional[list]:
        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

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

        api = self._server_manager.get_regular_api(doc_uri)

        message_matchers = [api.request_find_definition(doc_uri, line, col)]
        accepted_message_matchers = self._wait_for_message_matchers(message_matchers)
        message_matcher: IMessageMatcher
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
        from robotframework_ls.impl import snippets_completions

        doc_uri = kwargs["textDocument"]["uri"]
        # Note: 0-based
        line, col = kwargs["position"]["line"], kwargs["position"]["character"]

        document = self.workspace.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.critical("Unable to find document (%s) for completions." % (doc_uri,))
            return []

        api = self._server_manager.get_regular_api(doc_uri)

        ctx = CompletionContext(document, line, col, config=self.config)
        completions = []

        # Asynchronous completion.
        message_matchers = []
        message_matchers.append(api.request_complete_all(doc_uri, line, col))

        # These run locally (no need to get from the server).
        completions.extend(section_completions.complete(ctx))
        completions.extend(snippets_completions.complete(ctx))

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
