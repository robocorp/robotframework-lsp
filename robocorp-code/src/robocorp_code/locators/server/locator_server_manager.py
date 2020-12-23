from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import is_process_alive, log_and_silence_errors
import itertools
from functools import partial
import os
import sys
import threading
from typing import Any
from robocorp_code.protocols import ActionResultDict

log = get_logger(__name__)
_next_id = partial(next, itertools.count(0))


class LocatorServerManager:
    def __init__(self):
        self._curr_thread = threading.current_thread()
        self._server_process = None
        self._log_extension = ".locator"

    def _check_thread(self):
        curr_thread = threading.current_thread()
        if self._curr_thread is not curr_thread:
            raise AssertionError(
                f"This may only be called at the thread: {self._curr_thread}. Current thread: {curr_thread}"
            )

    def _get_api_client(self) -> Any:
        self._check_thread()
        server_process = self._server_process

        if server_process is not None:
            # If someone killed it, dispose of internal references
            # and create a new process.
            if not is_process_alive(server_process.pid):
                server_process = None
                self._dispose_server_process()

        if server_process is None:
            try:
                from robocorp_code.options import Setup
                from robocorp_code.locators.server.locator__main__ import (
                    start_server_process,
                )
                from robocorp_ls_core.jsonrpc.streams import (
                    JsonRpcStreamWriter,
                    JsonRpcStreamReader,
                )
                from robocorp_code.locators.server.locator_client import (
                    LocatorsApiClient,
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

                python_exe = sys.executable

                server_process = start_server_process(args=args, python_exe=python_exe)

                self._server_process = server_process

                write_to = server_process.stdin
                read_from = server_process.stdout
                w = JsonRpcStreamWriter(write_to, sort_keys=True)
                r = JsonRpcStreamReader(read_from)

                api = self._locators_api_client = LocatorsApiClient(
                    w, r, server_process
                )

                log.debug(
                    "Initializing locators api... (this pid: %s, api pid: %s).",
                    os.getpid(),
                    server_process.pid,
                )
                api.initialize(process_id=os.getpid())

            except Exception as e:
                if server_process is None:
                    log.exception(
                        "Error starting locators server api (server_process=None)."
                    )
                else:
                    exitcode = server_process.poll()
                    if exitcode is not None:
                        # Note: only read() if the process exited.
                        log.exception(
                            "Error starting locators server api. Exit code: %s Base exception: %s. Stderr: %s",
                            exitcode,
                            e,
                            server_process.stderr.read(),
                        )
                    else:
                        log.exception(
                            "Error (%s) starting locators server api (still running). Base exception: %s.",
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

        return self._locators_api_client

    @log_and_silence_errors(log)
    def _dispose_server_process(self):
        from robocorp_ls_core.basic import kill_process_and_subprocesses

        self._check_thread()
        try:
            log.debug("Dispose server process.")
            if self._server_process is not None:
                if is_process_alive(self._server_process.pid):
                    kill_process_and_subprocesses(self._server_process.pid)
        finally:
            self._server_process = None
            self._locators_api_client = None

    def browser_locator_start(self, headless=False) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            return api.browser_locator_start(headless=headless)
        return {
            "success": False,
            "message": "Unable to start locators server api.",
            "result": None,
        }

    def browser_locator_stop(self) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            return api.browser_locator_stop()
        return {
            "success": False,
            "message": "Unable to stop locators server api.",
            "result": None,
        }

    def browser_locator_pick(self) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            return api.browser_locator_pick()
        return {
            "success": False,
            "message": "Unable to browser pick locators server api.",
            "result": None,
        }

    def image_locator_pick(self) -> ActionResultDict:
        api = self._get_api_client()
        if api is not None:
            return api.image_locator_pick()
        return {
            "success": False,
            "message": "Unable to image pick locators server api.",
            "result": None,
        }
