import itertools
import os
import sys
import threading
from functools import partial
from typing import Optional

from robocorp_ls_core.basic import (
    is_process_alive,
    kill_process_and_subprocesses,
    log_and_silence_errors,
)
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.client import InspectorApiClient

log = get_logger(__name__)

_next_id = partial(next, itertools.count(0))


class InspectorServerManager(object):
    """
    Note: this is mainly a helper to manage the startup of an InspectorApiClient
    and restart it when needed.

    This class is not thread-safe and should be accessed only from a single thread.

    The provided `InspectorApiClient` may later be accessed from any thread.
    """

    def __init__(
        self,
        language_server_ref,
    ) -> None:
        self._main_thread = threading.current_thread()

        self._server_process = None

        self._inspector_api_client: Optional[InspectorApiClient] = None

        self._initializing = False
        self._log_extension = "inspector.api"
        self._language_server_ref = language_server_ref

    @property
    def stats(self) -> Optional[dict]:
        client = self._inspector_api_client
        if client is not None:
            return client.stats
        return None

    def _check_in_main_thread(self):
        curr_thread = threading.current_thread()
        if self._main_thread is not curr_thread:
            raise AssertionError(
                f"This may only be called at the thread: {self._main_thread}. "
                f"Current thread: {curr_thread}"
            )

    @property
    def robocorp_code_language_server(self):
        return self._language_server_ref()

    def get_inspector_api_client(self) -> Optional[InspectorApiClient]:
        from robocorp_code.inspector.inspector__main__ import start_server_process
        from robocorp_code.options import Setup
        from robocorp_code.robocorp_language_server import RobocorpLanguageServer

        self._check_in_main_thread()
        server_process = self._server_process

        if server_process is not None:
            # If someone killed it, dispose of internal references
            # and create a new process.
            if not is_process_alive(server_process.pid):
                server_process = None
                self._dispose_server_process()

        if server_process is None:
            try:
                from robocorp_ls_core.jsonrpc.streams import (
                    JsonRpcStreamReader,
                    JsonRpcStreamWriter,
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

                server_process = start_server_process(
                    args=args, python_exe=sys.executable
                )

                self._server_process = server_process

                write_to = server_process.stdin
                read_from = server_process.stdout
                w = JsonRpcStreamWriter(write_to, sort_keys=True)
                r = JsonRpcStreamReader(read_from)

                language_server_ref = self._language_server_ref

                def on_received_message(msg: dict) -> None:
                    method = msg.get("method")

                    if method in (
                        "$/customProgress",
                        "window/showMessage",
                        "$/webPick",
                        "$/webInspectorState",
                        "$/windowsPick",
                    ):
                        robocorp_code_language_server: Optional[
                            RobocorpLanguageServer
                        ] = language_server_ref()
                        if robocorp_code_language_server is not None:
                            robocorp_code_language_server.forward_msg(msg)

                api = self._inspector_api_client = InspectorApiClient(
                    w, r, server_process, on_received_message=on_received_message
                )

                log.debug(
                    "Initializing api... (this pid: %s, api pid: %s).",
                    os.getpid(),
                    server_process.pid,
                )
                api.initialize(
                    process_id=os.getpid(),
                )

            except Exception as e:
                if server_process is None:
                    log.exception(
                        "Error starting inspector server api (server_process=None)."
                    )
                else:
                    exitcode = server_process.poll()
                    if exitcode is not None:
                        # Note: only read() if the process exited.
                        log.exception(
                            "Error starting inspector server api. Exit code: %s Base exception: %s. Stderr: %s",
                            exitcode,
                            e,
                            server_process.stderr.read(),
                        )
                    else:
                        log.exception(
                            "Error (%s) starting inspector server api (still running). Base exception: %s.",
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
                    log.debug("server_process == None in get_inspector_api_client()")

        return self._inspector_api_client

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
            self._inspector_api_client = None

    @log_and_silence_errors(log)
    def exit(self):
        self._check_in_main_thread()
        if self._inspector_api_client is not None:
            # i.e.: only exit if it was started in the first place.
            self._inspector_api_client.exit()
        self._dispose_server_process()

    @log_and_silence_errors(log)
    def shutdown(self):
        self._check_in_main_thread()
        if self._inspector_api_client is not None:
            # i.e.: only shutdown if it was started in the first place.
            self._inspector_api_client.shutdown()
