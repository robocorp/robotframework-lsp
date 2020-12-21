from robocorp_ls_core.pluginmanager import PluginManager
import threading
from robocorp_ls_core.basic import (
    log_and_silence_errors,
    kill_process_and_subprocesses,
    is_process_alive,
)
import sys
import weakref
import os
from robocorp_ls_core.robotframework_log import get_logger
from typing import Any, Dict, Optional, Tuple
from robotframework_ls.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
)
from robocorp_ls_core.protocols import (
    IConfig,
    IMessageMatcher,
    IWorkspace,
    IRobotFrameworkApiClient,
)
import itertools
from functools import partial

DEFAULT_API_ID = "default"

log = get_logger(__name__)

_next_id = partial(next, itertools.count(0))


class _ServerApi(object):
    """
    Note: this is mainly a helper to manage the startup of an IRobotFrameworkApiClient
    and restart it when needed.
    
    This class is not thread-safe and should be accessed only from a single thread.
    
    The provided `IRobotFrameworkApiClient` may later be accessed from any thread.
    """

    def __init__(self, log_extension, language_server_ref):
        self._main_thread = threading.current_thread()

        from robotframework_ls.robot_config import RobotConfig

        self._used_python_executable = None
        self._used_environ = None
        self._server_process = None
        self._robotframework_api_client: Optional[IRobotFrameworkApiClient] = None

        # We have a version of the config with the settings passed overridden
        # by the settings of a given (customized) interpreter.
        self._config: IConfig = RobotConfig()

        self.workspace = None
        self._initializing = False
        self._log_extension = log_extension
        self._language_server_ref = language_server_ref
        self._interpreter_info: Optional[IInterpreterInfo] = None

    def _check_in_main_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"This may only be called at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    @property
    def robot_framework_language_server(self):
        return self._language_server_ref()

    @property
    def workspace(self) -> IWorkspace:
        return self._workspace

    @workspace.setter
    def workspace(self, workspace: IWorkspace):
        self._check_in_main_thread()
        self._workspace = workspace

    @property
    def config(self) -> IConfig:
        return self._config

    @config.setter
    def config(self, config: IConfig):
        self._check_in_main_thread()
        self._config.update(config.get_full_settings())
        self._check_reinitialize_and_forward_settings_if_needed()

    def set_interpreter_info(self, interpreter_info: IInterpreterInfo) -> None:
        self._check_in_main_thread()
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_PYTHON_EXECUTABLE,
        )
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

        self._interpreter_info = interpreter_info

        if interpreter_info is not None:
            overridden_settings: dict = {}
            python_exe = interpreter_info.get_python_exe()
            if python_exe:
                overridden_settings[OPTION_ROBOT_PYTHON_EXECUTABLE] = python_exe

            environ = interpreter_info.get_environ()
            if environ:
                overridden_settings[OPTION_ROBOT_PYTHON_ENV] = environ

            additional_pythonpath_entries = (
                interpreter_info.get_additional_pythonpath_entries()
            )
            if additional_pythonpath_entries:
                overridden_settings[
                    OPTION_ROBOT_PYTHONPATH
                ] = additional_pythonpath_entries

            self._config.set_override_settings(overridden_settings)
        else:
            self._config.set_override_settings({})

        self._check_reinitialize_and_forward_settings_if_needed()

    def _check_reinitialize_and_forward_settings_if_needed(self) -> None:
        self._check_in_main_thread()
        was_disposed = self._check_reinitialize()
        if not was_disposed:
            # i.e.: when the interpreter info changes, even if it kept the same
            # interpreter, it's possible that the configuration changed.
            self.forward(
                "workspace/didChangeConfiguration",
                {"settings": self._config.get_full_settings()},
            )

    def _check_reinitialize(self) -> bool:
        """
        Returns True if the existing process was disposed (or if it wasn't even
        started) and False if the existing process was kept running.
        """
        self._check_in_main_thread()
        if self._server_process is None:
            return True

        # If the python executable changes, restart the server API.
        if self._used_python_executable is not None:
            python_executable = self._get_python_executable()
            if python_executable != self._used_python_executable:
                # It'll be reinitialized when needed.
                self._dispose_server_process()
                return True
        if self._used_environ is not None:
            environ = self._get_environ()
            if environ != self._used_environ:
                # It'll be reinitialized when needed.
                self._dispose_server_process()
                return True
        return False

    def _get_python_executable(self) -> str:
        self._check_in_main_thread()
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
            log.warning(f"self._config not set in {self.__class__}")
        return python_exe

    def _get_environ(self) -> Dict[str, str]:
        self._check_in_main_thread()
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

    def get_robotframework_api_client(self) -> Optional[IRobotFrameworkApiClient]:
        self._check_in_main_thread()
        workspace = self.workspace
        assert (
            workspace
        ), "The workspace must be already set when getting the server api."

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
                from robotframework_ls.server_api.client import RobotFrameworkApiClient
                from robotframework_ls.server_api.server__main__ import (
                    start_server_process,
                )
                from robocorp_ls_core.jsonrpc.streams import (
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
                        args.append(
                            "--log-file=" + Setup.options.log_file + self._log_extension
                        )
                    else:
                        args.append(
                            "--log-file="
                            + Setup.options.log_file
                            + (".%s" % (log_id,))
                            + self._log_extension
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

                api = self._robotframework_api_client = RobotFrameworkApiClient(
                    w, r, server_process
                )

                log.debug(
                    "Initializing api... (this pid: %s, api pid: %s).",
                    os.getpid(),
                    server_process.pid,
                )
                api.initialize(
                    process_id=os.getpid(),
                    root_uri=workspace.root_uri,
                    workspace_folders=list(
                        {"uri": folder.uri, "name": folder.name}
                        for folder in workspace.iter_folders()
                    ),
                )

                config = self._config
                log.debug("Forwarding config to api...")
                if config is not None:
                    api.forward(
                        "workspace/didChangeConfiguration",
                        {"settings": config.get_full_settings()},
                    )

                # Open existing documents in the API.
                source: Optional[str]
                for document in workspace.iter_documents():
                    log.debug("Forwarding doc: %s to api...", document.uri)
                    try:
                        source = document.source
                    except Exception:
                        source = None

                    api.forward(
                        "textDocument/didOpen",
                        {
                            "textDocument": {
                                "uri": document.uri,
                                "version": document.version,
                                "text": source,
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
                            "Error starting robotframework server api. Exit code: %s Base exception: %s. Stderr: %s",
                            exitcode,
                            e,
                            server_process.stderr.read(),
                        )
                    else:
                        log.exception(
                            "Error (%s) starting robotframework server api (still running). Base exception: %s.",
                            exitcode,
                            e,
                        )
                self._dispose_server_process()
            finally:
                if server_process is not None:
                    log.debug(
                        "Server api (%s) created pid: %s", self, server_process.pid
                    )
                else:
                    log.debug(
                        "server_process == None in get_robotframework_api_client()"
                    )

        return self._robotframework_api_client

    @log_and_silence_errors(log)
    def _dispose_server_process(self):
        self._check_in_main_thread()
        try:
            log.debug("Dispose server process.")
            if self._server_process is not None:
                if is_process_alive(self._server_process.pid):
                    kill_process_and_subprocesses(self._server_process.pid)
        finally:
            self._server_process = None
            self._robotframework_api_client = None
            self._used_environ = None
            self._used_python_executable = None

    def request_cancel(self, message_id) -> None:
        self._check_in_main_thread()
        api = self.get_robotframework_api_client()
        if api is not None:
            api.request_cancel(message_id)

    @log_and_silence_errors(log)
    def forward(self, method_name, params) -> None:
        self._check_in_main_thread()
        api = self.get_robotframework_api_client()
        if api is not None:
            api.forward(method_name, params)

    @log_and_silence_errors(log)
    def forward_async(self, method_name, params) -> Optional[IMessageMatcher]:
        self._check_in_main_thread()
        api = self.get_robotframework_api_client()
        if api is not None:
            return api.forward_async(method_name, params)
        return None

    @log_and_silence_errors(log)
    def open(self, uri, version, source):
        self._check_in_main_thread()
        api = self.get_robotframework_api_client()
        if api is not None:
            api.open(uri, version, source)

    @log_and_silence_errors(log)
    def exit(self):
        self._check_in_main_thread()
        if self._robotframework_api_client is not None:
            # i.e.: only exit if it was started in the first place.
            self._robotframework_api_client.exit()
        self._dispose_server_process()

    @log_and_silence_errors(log)
    def shutdown(self):
        self._check_in_main_thread()
        if self._robotframework_api_client is not None:
            # i.e.: only shutdown if it was started in the first place.
            self._robotframework_api_client.shutdown()


class _RegularAndLintApi(object):
    def __init__(self, api, lint_api):
        self.api = api
        self.lint_api = lint_api

    def __iter__(self):
        yield self.api
        yield self.lint_api

    def set_interpreter_info(self, interpreter_info: IInterpreterInfo):
        for api in self:
            api.set_interpreter_info(interpreter_info)


class ServerManager(object):
    """
    Note: accessing the ServerManager may only be done from a single thread.
    
    The idea is that clients do something as:
    
    rf_api_client = server_manager.get_lint_rf_api_client(doc_uri)
    if rf_api_client is not None:
        ... robotframework_api_client may then be accessed by any thread.
    """

    def __init__(
        self,
        pm: PluginManager,
        config: Optional[IConfig] = None,
        workspace: Optional[IWorkspace] = None,
        language_server: Optional[Any] = None,
    ):
        self._main_thread = threading.current_thread()
        self._config: Optional[IConfig] = config
        self._workspace: Optional[IWorkspace] = workspace
        self._pm = pm
        self._id_to_apis: Dict[str, _RegularAndLintApi] = {}
        if language_server is None:
            self._language_server_ref = lambda: None
        else:
            self._language_server_ref = weakref.ref(language_server)

    def _check_in_main_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"This may only be called at the thread: {self._main_thread}. Current thread: {curr_thread}"
            )

    def _iter_all_apis(self):
        self._check_in_main_thread()
        for apis in self._id_to_apis.values():
            for api in apis:
                yield api

    def set_config(self, config: IConfig) -> None:
        self._check_in_main_thread()
        self._config = config
        for api in self._iter_all_apis():
            api.config = config

    def set_workspace(self, workspace: IWorkspace) -> None:
        self._check_in_main_thread()
        self._workspace = workspace
        for api in self._iter_all_apis():
            api.workspace = workspace

    def _create_apis(self, api_id) -> _RegularAndLintApi:
        self._check_in_main_thread()
        assert api_id not in self._id_to_apis, f"{api_id} already created."
        api = _ServerApi(".api", self._language_server_ref)
        lint_api = _ServerApi(".lint.api", self._language_server_ref)

        config = self._config
        if config is not None:
            api.config = config
            lint_api.config = config

        workspace = self._workspace
        if workspace is not None:
            api.workspace = workspace
            lint_api.workspace = workspace

        apis = _RegularAndLintApi(api, lint_api)
        self._id_to_apis[api_id] = apis
        return apis

    def _get_default_apis(self) -> _RegularAndLintApi:
        self._check_in_main_thread()
        apis = self._id_to_apis.get(DEFAULT_API_ID)
        if not apis:
            apis = self._create_apis(DEFAULT_API_ID)
        return apis

    def _get_apis_for_doc_uri(self, doc_uri: str) -> _RegularAndLintApi:
        self._check_in_main_thread()
        for ep in self._pm.get_implementations(EPResolveInterpreter):
            interpreter_info = ep.get_interpreter_info_for_doc_uri(doc_uri)
            if interpreter_info is not None:
                # Note: we currently only identify things through the interpreter
                # id, but a potential optimization would be using the same python
                # executable in different APIs if they match.
                interpreter_id = interpreter_info.get_interpreter_id()
                apis = self._id_to_apis.get(interpreter_id)
                if apis is not None:
                    apis.set_interpreter_info(interpreter_info)
                else:
                    apis = self._create_apis(interpreter_id)
                    apis.set_interpreter_info(interpreter_info)

                return apis

        return self._get_default_apis()

    def forward(self, target: Tuple[str, ...], method_name: str, params: Any) -> None:
        self._check_in_main_thread()
        apis: _RegularAndLintApi
        for apis in self._id_to_apis.values():
            if "api" in target:
                apis.api.forward(method_name, params)

            if "lint" in target:
                # For the lint api, things should be asynchronous.
                apis.lint_api.forward_async(method_name, params)

    def shutdown(self) -> None:
        self._check_in_main_thread()
        for api in self._iter_all_apis():
            api.shutdown()

    def exit(self) -> None:
        self._check_in_main_thread()
        for api in self._iter_all_apis():
            api.exit()

    # Private APIs

    def _get_source_format_api(self, doc_uri: str) -> _ServerApi:
        self._check_in_main_thread()
        apis = self._get_apis_for_doc_uri(doc_uri)
        return apis.api

    def _get_lint_api(self, doc_uri: str) -> _ServerApi:
        self._check_in_main_thread()
        apis = self._get_apis_for_doc_uri(doc_uri)
        return apis.lint_api

    def _get_regular_api(self, doc_uri: str) -> _ServerApi:
        self._check_in_main_thread()
        apis = self._get_apis_for_doc_uri(doc_uri)
        return apis.api

    # Public APIs -- returns a client that can be accessed in any thread

    def get_lint_rf_api_client(
        self, doc_uri: str
    ) -> Optional[IRobotFrameworkApiClient]:
        api = self._get_lint_api(doc_uri)
        if api is not None:
            return api.get_robotframework_api_client()
        return None

    def get_regular_rf_api_client(
        self, doc_uri: str
    ) -> Optional[IRobotFrameworkApiClient]:
        api = self._get_regular_api(doc_uri)
        if api is not None:
            return api.get_robotframework_api_client()
        return None

    def get_source_format_rf_api_client(
        self, doc_uri
    ) -> Optional[IRobotFrameworkApiClient]:
        api = self._get_source_format_api(doc_uri)
        if api is not None:
            return api.get_robotframework_api_client()
        return None

    def get_workspace_symbols_api_client(self) -> Optional[IRobotFrameworkApiClient]:
        self._check_in_main_thread()
        apis = self._get_default_apis()
        return apis.api.get_robotframework_api_client()
