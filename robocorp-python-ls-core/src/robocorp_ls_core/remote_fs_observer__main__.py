"""
This module provides a way to create a service which will listen for changes
on folders on the filesystem and will provide notifications of those to listeners.
"""
import os
import sys
import argparse
import threading
import socket as socket_module
from typing import Optional, Tuple

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]

# ==============================================================================
# Starting up as main below
# ==============================================================================

LOG_FORMAT = "%(asctime)s UTC pid: %(process)d - %(threadName)s - %(levelname)s - %(name)s\n%(message)s\n\n"

_critical_error_log_file = os.path.join(
    os.path.expanduser("~"), "remote_fs_observer_critical.log"
)


def add_arguments(parser):
    parser.description = "Remote FS Observer"

    parser.add_argument(
        "--log-file",
        help="Redirect logs to the given file instead of writing to stderr (i.e.: c:/temp/my_log.log).",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity of log output (i.e.: -vv).",
    )


class ObserverProvider(object):
    def __init__(self):
        from robocorp_ls_core.watchdog_wrapper import IFSObserver

        self._observer: Optional[IFSObserver] = None

    @property
    def observer(self):
        return self._observer

    def initialize_observer(self, backend, extensions: Optional[Tuple[str, ...]]):
        from robocorp_ls_core import watchdog_wrapper

        assert self._observer is None
        self._observer = watchdog_wrapper.create_observer(
            backend, extensions=extensions
        )
        return self._observer


class _RemoteFSServer(threading.Thread):
    def __init__(
        self, socket: socket_module.socket, observer_provider: ObserverProvider
    ) -> None:
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamWriter
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader
        from typing import Dict
        from robocorp_ls_core.watchdog_wrapper import IFSWatch

        threading.Thread.__init__(self)
        self.name = "_RemoteFSServer"
        self.socket = socket

        self.writer: Optional[JsonRpcStreamWriter] = None
        self.reader: Optional[JsonRpcStreamReader] = None
        self._observer_provider: ObserverProvider = observer_provider
        self.on_change_id_to_watch: Dict[int, IFSWatch] = {}

    def _on_change(self, src_path, on_change_id):
        # Note: this will be called from the watcher thread.
        if not self.writer.write(
            {"command": "on_change", "on_change_id": on_change_id, "src_path": src_path}
        ):
            from robocorp_ls_core.watchdog_wrapper import IFSWatch

            # I.e.: socket communication appears to be dropped for this change_id,
            # so, stop tracking it.
            watch: IFSWatch = self.on_change_id_to_watch.pop(on_change_id, None)
            if watch is not None:
                watch.stop_tracking()

    def run(self):
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamWriter
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader

        s = self.socket
        write_to = s.makefile("wb")
        read_from = s.makefile("rb")

        w = JsonRpcStreamWriter(write_to, sort_keys=True)
        r = JsonRpcStreamReader(read_from)
        self.writer = w
        self.reader = r

        r.listen(self._on_read)

    def _on_read(self, msg):
        command = msg.get("command")
        if command == "initialize":
            from robocorp_ls_core.basic import exit_when_pid_exists

            parent_pid = msg["parent_pid"]
            if parent_pid not in (None, -1, 0):
                exit_when_pid_exists(parent_pid)

            backend = msg["backend"]
            extensions = msg["extensions"]
            if extensions is not None:
                extensions = tuple(extensions)

            self._observer_provider.initialize_observer(backend, extensions)
            # initialize requires an acknowledgement.
            self.writer.write({"command": "ack_initialize"})

        elif command == "initialize_connect":
            # just used to send an initialize acknowledgement.
            self.writer.write({"command": "ack_initialize"})

        elif command == "stop_tracking":
            from robocorp_ls_core.watchdog_wrapper import IFSWatch

            on_change_id = msg["on_change_id"]
            watch: IFSWatch = self.on_change_id_to_watch.pop(on_change_id, None)
            if watch is not None:
                watch.stop_tracking()

        elif command == "notify_on_any_change":
            from robocorp_ls_core.watchdog_wrapper import PathInfo

            on_change_id = msg["on_change_id"]
            paths = [PathInfo(p["path"], p["recursive"]) for p in msg["paths"]]
            extensions = msg["extensions"]
            if extensions is not None:
                extensions = tuple(extensions)

            observer = self._observer_provider.observer
            self.on_change_id_to_watch[on_change_id] = observer.notify_on_any_change(
                paths, self._on_change, call_args=(on_change_id,), extensions=extensions
            )
            # notify_on_any_change requires an acknowledgement.
            self.writer.write(
                {"command": "ack_notify_on_any_change", "on_change_id": on_change_id}
            )


def main():
    try:
        import robocorp_ls_core
    except ImportError:
        # Automatically add it to the path if this module is being executed.
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import robocorp_ls_core  # @UnusedImport

    from robocorp_ls_core.robotframework_log import (
        configure_logger,
        log_args_and_python,
        get_logger,
    )

    parser = argparse.ArgumentParser()
    add_arguments(parser)

    original_args = sys.argv[1:]
    args = parser.parse_args(args=original_args)

    verbose = args.verbose
    log_file = args.log_file or ""

    if not log_file:
        # If not specified in args, also check the environment variables.
        log_file = os.environ.get("REMOTE_FS_OBSERVER_LOG_FILE", "")
        if log_file:
            verbose = 2

    configure_logger("remote_fs_observer", verbose, log_file)
    log = get_logger("robocorp_ls_core.remote_fs_observer__main__")
    log_args_and_python(log, original_args, robocorp_ls_core)

    # Ok, the initial structure is in place, let's start listening for connections.
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen()

    # Print the port where the server is listening so that clients can connect to it.
    stdout_buffer = sys.__stdout__.buffer
    stdout_buffer.write(f"port: {s.getsockname()[1]}\n".encode("utf-8"))
    stdout_buffer.flush()

    observer_provider = ObserverProvider()
    while True:
        conn, _addr = s.accept()
        server = _RemoteFSServer(conn, observer_provider)
        server.start()


if __name__ == "__main__":
    try:
        if sys.version_info[0] <= 2:
            raise AssertionError(
                "Python 3+ is required for the RobotFramework Language Server.\nCurrent executable: "
                + sys.executable
            )
        main()
    except (SystemExit, KeyboardInterrupt):
        pass
    except:
        # Critical error (the logging may not be set up properly).
        import traceback

        # Print to file and stderr.
        with open(_critical_error_log_file, "a+") as stream:
            traceback.print_exc(file=stream)

        traceback.print_exc()
