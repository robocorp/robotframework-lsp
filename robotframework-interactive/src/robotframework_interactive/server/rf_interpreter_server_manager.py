from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import is_process_alive, log_and_silence_errors
import itertools
from functools import partial
import os
import sys
import threading
from typing import Any, Dict, Optional
from robocorp_ls_core.protocols import ActionResultDict, IConfig
from robocorp_ls_core.options import DEFAULT_TIMEOUT, USE_TIMEOUTS, NO_TIMEOUT

log = get_logger(__name__)
_next_id = partial(next, itertools.count(0))


def create_server_socket(host, port):
    try:
        import socket as socket_module

        server = socket_module.socket(
            socket_module.AF_INET, socket_module.SOCK_STREAM, socket_module.IPPROTO_TCP
        )
        if sys.platform == "win32":
            server.setsockopt(
                socket_module.SOL_SOCKET, socket_module.SO_EXCLUSIVEADDRUSE, 1
            )
        else:
            server.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_REUSEADDR, 1)

        server.bind((host, port))
    except Exception:
        server.close()  # i.e.: close (we just accept 1 connection).
        raise

    return server


class RfInterpreterServerManager:
    def __init__(
        self,
        verbose: int = 0,
        base_log_file: str = "",
        on_interpreter_message=None,
        uri: str = "",
    ):
        from robotframework_interactive.server.rf_interpreter_ls_config import (
            RfInterpreterRobotConfig,
        )
        from robocorp_ls_core import uris

        assert uri
        self._uri = uri
        self._filename = uris.to_fs_path(uri)
        self._lock_api_client = threading.RLock()
        self._server_process = None
        self._log_extension = ".rf_interpreter"
        self._disposed = False
        # The config allows clients to set the python executable/env.
        self._config: IConfig = RfInterpreterRobotConfig()

        self._verbose = verbose
        self._base_log_file = base_log_file
        self._on_interpreter_message = on_interpreter_message

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def config(self) -> IConfig:
        return self._config

    @config.setter
    def config(self, config: IConfig):
        with self._lock_api_client:
            self._config.update(config.get_full_settings())

    def _get_python_executable(self) -> str:
        with self._lock_api_client:
            from robotframework_interactive.server.rf_interpreter_ls_config import (
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
        from robotframework_interactive.server.rf_interpreter_ls_config import (
            OPTION_ROBOT_PYTHON_ENV,
            OPTION_ROBOT_PYTHONPATH,
        )

        with self._lock_api_client:
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

                pythonpath_entries = config.get_setting(
                    OPTION_ROBOT_PYTHONPATH, list, []
                )
                if pythonpath_entries:
                    # if robot.pythonpath is defined, append those entries to
                    # the PYTHONPATH env variable when starting the interactive
                    # console.
                    current_pythonpath = env.get("PYTHONPATH", "")
                    if not current_pythonpath:
                        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
                    else:
                        existing = set(current_pythonpath.split(os.pathsep))
                        env["PYTHONPATH"] = (
                            current_pythonpath
                            + os.pathsep
                            + os.pathsep.join(
                                (
                                    str(x)
                                    for x in pythonpath_entries
                                    if x not in existing
                                )
                            )
                        )
            else:
                log.warning("self._config not set in %s" % (self.__class__,))
            return env

    def _get_api_client(self) -> Any:
        with self._lock_api_client:
            server_process = self._server_process

            if server_process is not None:
                # If someone killed it, dispose of internal references
                # and create a new process.
                if not is_process_alive(server_process.pid):
                    self._dispose_server_process()

            if self._disposed:
                log.info("Robot Framework Interpreter server already disposed.")
                return None

            if server_process is None:
                try:
                    from robotframework_interactive.server.rf_interpreter__main__ import (
                        start_server_process,
                    )
                    from robocorp_ls_core.jsonrpc.streams import (
                        JsonRpcStreamWriter,
                        JsonRpcStreamReader,
                    )
                    from robotframework_interactive.server.rf_interpreter_client import (
                        RfInterpreterApiClient,
                    )

                    args = []
                    if self._verbose:
                        args.append("-" + "v" * int(self._verbose))
                    if self._base_log_file:
                        log_id = _next_id()
                        # i.e.: use a log id in case we create more than one in the
                        # same session.
                        if log_id == 0:
                            args.append(
                                "--log-file="
                                + self._base_log_file
                                + self._log_extension
                            )
                        else:
                            args.append(
                                "--log-file="
                                + self._base_log_file
                                + (".%s" % (log_id,))
                                + self._log_extension
                            )

                    python_exe = self._get_python_executable()
                    environ = self._get_environ()
                    connect_event = threading.Event()

                    s = create_server_socket(host="127.0.0.1", port=0)
                    import socket as socket_module

                    new_socket: Optional[socket_module.socket] = None
                    connect_event = threading.Event()

                    def wait_for_connection():
                        nonlocal new_socket
                        try:
                            s.settimeout(
                                DEFAULT_TIMEOUT if USE_TIMEOUTS else NO_TIMEOUT
                            )
                            s.listen(1)
                            new_socket, _addr = s.accept()
                            log.info("Connection accepted")
                        except:
                            log.exception("Server did not connect.")
                        finally:
                            connect_event.set()
                            s.close()

                    t = threading.Thread(target=wait_for_connection)
                    t.start()

                    # Now, we're listening, let's start up the interpreter to connect back.
                    _, port = s.getsockname()
                    args.append("--tcp")
                    args.append("--host")
                    args.append("127.0.0.1")
                    args.append("--port")
                    args.append(str(port))

                    cwd = os.path.dirname(self._filename)
                    if not os.path.isdir(cwd):
                        raise AssertionError(f"CWD passed is not a directory: {cwd}")

                    server_process = start_server_process(
                        args=args, python_exe=python_exe, env=environ, cwd=cwd
                    )

                    self._server_process = server_process

                    connect_event.wait()
                    if new_socket is None:
                        raise RuntimeError(
                            "Timed out while waiting for interpreter server to connect."
                        )

                    read_from = new_socket.makefile("rb")
                    write_to = new_socket.makefile("wb")

                    w = JsonRpcStreamWriter(write_to, sort_keys=True)
                    r = JsonRpcStreamReader(read_from)

                    api = self._rf_interpreter_api_client = RfInterpreterApiClient(
                        w,
                        r,
                        server_process,
                        on_interpreter_message=self._on_interpreter_message,
                    )

                    log.debug(
                        "Initializing rf interpreter api... (this pid: %s, api pid: %s).",
                        os.getpid(),
                        server_process.pid,
                    )
                    api.initialize(process_id=os.getpid())

                except Exception as e:
                    if server_process is None:
                        log.exception(
                            "Error starting rf interpreter server api (server_process=None)."
                        )
                    else:
                        exitcode = server_process.poll()
                        if exitcode is not None:
                            # Note: only read() if the process exited.
                            log.exception(
                                "Error starting rf interpreter server api. Exit code: %s Base exception: %s. Stderr: %s",
                                exitcode,
                                e,
                                server_process.stderr.read(),
                            )
                        else:
                            log.exception(
                                "Error (%s) starting rf interpreter server api (still running). Base exception: %s.",
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
                        log.debug("server_process == None in _get_api_client()")

            return self._rf_interpreter_api_client

    @log_and_silence_errors(log)
    def _dispose_server_process(self):
        from robocorp_ls_core.basic import kill_process_and_subprocesses

        with self._lock_api_client:
            try:
                log.debug("Dispose server process.")
                if self._server_process is not None:
                    if is_process_alive(self._server_process.pid):
                        kill_process_and_subprocesses(self._server_process.pid)
            finally:
                self._disposed = True
                self._server_process = None
                self._rf_interpreter_api_client = None

    def interpreter_start(
        self, uri: str, workspace_root_path: str = None
    ) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            settings = self._config.get_full_settings()
            return api.interpreter_start(uri, settings, workspace_root_path)
        return {
            "success": False,
            "message": "Unable to start Robot Framework Interpreter server api.",
            "result": None,
        }

    @property
    def waiting_input(self):
        api = self._get_api_client()
        if api is not None:
            return api.waiting_input
        return False

    def interpreter_evaluate(self, code: str) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            return api.interpreter_evaluate(code)
        return {
            "success": False,
            "message": "Robot Framework Interpreter server api not available.",
            "result": None,
        }

    def interpreter_compute_evaluate_text(
        self, code: str, target_type: str = "evaluate"
    ) -> ActionResultDict:
        """
        :param target_type:
            'evaluate': means that the target is an evaluation with the given code.
                This implies that the current code must be changed to make sense
                in the given context.

            'completions': means that the target is a code-completion
                This implies that the current code must be changed to include
                all previous successful evaluations so that the code-completion
                contains the full information up to the current point.
        """
        api = self._get_api_client()
        if api is not None:
            return api.interpreter_compute_evaluate_text(code, target_type)
        return {
            "success": False,
            "message": "Robot Framework Interpreter server api not available.",
            "result": None,
        }

    def interpreter_stop(self):
        api = self._get_api_client()
        if api is not None:
            try:
                return api.interpreter_stop()
            finally:
                # After a stop, also dispose the process. It can't be reused
                # (a new manager must be created).
                self._dispose_server_process()
        return {
            "success": False,
            "message": "Unable to stop Robot Framework Interpreter server api.",
            "result": None,
        }
