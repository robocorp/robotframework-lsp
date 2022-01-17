import itertools
import socket as socket_module
import sys
import time
import random
import threading
from functools import partial
from typing import Optional, List, Dict, Tuple, Sequence

from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.watchdog_wrapper import PathInfo, IFSCallback, IFSWatch
import os

log = get_logger(__name__)


class _RemoteFSWatch(object):
    """
    Holds together the information related to watching a filesystem path
    along with a way to stop watching it.
    """

    def __init__(
        self,
        remote_fs_observer: "RemoteFSObserver",
        on_change_id: str,
        on_change: IFSCallback,
        call_args=(),
    ):
        self.remote_fs_observer = remote_fs_observer
        self.on_change_id = on_change_id
        self.on_change = on_change
        self.call_args = call_args
        self.acknowledged = threading.Event()

    def stop_tracking(self):
        # Note that to stop tracking we actually send a message back saying
        # that the remote server should stop tracking a given path.
        remote_fs_observer = self.remote_fs_observer
        if remote_fs_observer is not None:
            self.remote_fs_observer = None
            writer = remote_fs_observer.writer
            if writer is not None:
                writer.write(
                    {"command": "stop_tracking", "on_change_id": self.on_change_id}
                )

            # Also remove from the parent.
            remote_fs_observer._change_id_to_fs_watch.pop(self.on_change_id, None)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSWatch = check_implements(self)


class RemoteFSObserver(object):
    def __init__(self, backend: str, extensions: Optional[Tuple[str, ...]]):
        import subprocess
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamWriter

        self.process: Optional[subprocess.Popen] = None
        self.port: Optional[int] = None
        self.reader: Optional[JsonRpcStreamReader] = None
        self.writer: Optional[JsonRpcStreamWriter] = None
        self.reader_thread: Optional[threading.Thread] = None

        self._counter: "partial[int]" = partial(next, itertools.count())
        self._change_id_to_fs_watch: Dict[str, _RemoteFSWatch] = {}

        self._socket: Optional[socket_module.socket] = None
        self._backend = backend
        self._extensions = extensions
        self._initialized_event = threading.Event()

    def _next_id(self) -> str:
        return f"{os.getpid()} - {self._counter()} - {random.random()}"

    def start_server(
        self, log_file: Optional[str] = None, verbose: Optional[int] = None
    ) -> int:
        """
        :return int:
            The port used by the server (which may later be used to connect
            from another observer through connect_to_server).
        """
        assert self.port is None, "RemoteFSObserver already initialized."
        import subprocess
        from robocorp_ls_core import remote_fs_observer__main__

        args = [sys.executable, "-u", remote_fs_observer__main__.__file__]
        if log_file:
            args.append(f"--log-file={log_file}")

        if verbose:
            args.append("-" + ("v" * verbose))

        log.info("Initializing Remote FS Observer with the following args: %s", args)
        process = self.process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        stdout = process.stdout
        assert stdout

        port_out = []
        read_port_thread_finished = threading.Event()

        def read_port():
            try:
                retcode = process.poll()

                while retcode is None:
                    contents = stdout.readline().strip()
                    if not contents:
                        log.info(
                            "Read empty string from Remote FS Observer process launched with: %s",
                            args,
                        )
                        time.sleep(0.1)
                        retcode = process.poll()
                    else:
                        if not contents.startswith(b"port:"):
                            log.critical(
                                f'Expected the read contents from Remote FS Observer to start with "port:". Found: {contents!r}'
                            )
                            continue

                        contents = contents[5:].strip()
                        port = int(contents)
                        port_out.append(port)
                        return

                # If it got here the process exited (and we didn't get the port).
                log.critical(
                    f"The Remote FS Observer process launched with: {args} exited without providing a port. retcode: {retcode}"
                )
            except:
                log.exception("Error reading port from Remote FS Observer.")
            finally:
                read_port_thread_finished.set()

        def read_fs_observer_stderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode("utf-8", "replace")
                sys.stderr.write(line)
                log.debug("Remote FS observer stderr: %s", line)

        t = threading.Thread(target=read_fs_observer_stderr)
        t.daemon = True
        t.start()

        t = threading.Thread(target=read_port)
        t.daemon = True
        t.start()

        if not read_port_thread_finished.wait(15):
            raise AssertionError(
                "Unable to read port from Remote FS Observer after 15 seconds."
            )

        if not port_out:
            raise AssertionError(
                "Remote FS Observer finished without providing a port."
            )

        port = self.port = port_out[0]
        self._initialize_reader_and_writer()
        assert self.writer, "Writer not properly initialized!"
        self.writer.write(
            {
                "command": "initialize",
                "backend": self._backend,
                "extensions": self._extensions,
                "parent_pid": os.getpid(),
            }
        )
        if not self._initialized_event.wait(5):
            raise RuntimeError("Unable to initialize server.")
        return port

    def connect_to_server(self, port: int):
        assert self.port is None, "RemoteFSObserver already initialized."

        self.port = port
        self._initialize_reader_and_writer()
        assert self.writer, "Writer not properly initialized!"
        self.writer.write({"command": "initialize_connect"})  # just used for the ack.
        if not self._initialized_event.wait(5):
            raise RuntimeError("Unable to initialize server.")

    def _initialize_reader_and_writer(self):
        assert self.writer is None
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamWriter
        from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader

        s = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
        try:
            # Configure the socket accordingly so that the connection is
            # properly kept alive.
            IPPROTO_TCP, SO_KEEPALIVE, TCP_KEEPIDLE, TCP_KEEPINTVL, TCP_KEEPCNT = (
                socket_module.IPPROTO_TCP,
                socket_module.SO_KEEPALIVE,
                socket_module.TCP_KEEPIDLE,  # @UndefinedVariable
                socket_module.TCP_KEEPINTVL,  # @UndefinedVariable
                socket_module.TCP_KEEPCNT,  # @UndefinedVariable
            )
            s.setsockopt(socket_module.SOL_SOCKET, SO_KEEPALIVE, 1)
            s.setsockopt(IPPROTO_TCP, TCP_KEEPIDLE, 1)
            s.setsockopt(IPPROTO_TCP, TCP_KEEPINTVL, 3)
            s.setsockopt(IPPROTO_TCP, TCP_KEEPCNT, 5)
        except AttributeError:
            pass  # May not be available everywhere.

        s.connect(("127.0.0.1", self.port))
        self._socket = s
        write_to = s.makefile("wb")
        read_from = s.makefile("rb")

        w = JsonRpcStreamWriter(write_to, sort_keys=True)
        r = JsonRpcStreamReader(read_from)
        self.writer = w
        self.reader = r

        self.reader_thread = threading.Thread(
            target=self.reader.listen, args=(self._on_read,)
        )
        self.reader_thread.daemon = True
        self.reader_thread.start()

    def dispose(self):
        s = self._socket
        if s is not None:
            try:
                s.shutdown()
                s.close()
            except Exception:
                pass
            self._socket = None
        process = self.process
        if process:
            self.process.kill()
            self.process = None

    def notify_on_any_change(
        self,
        paths: List[PathInfo],
        on_change: IFSCallback,
        call_args=(),
        extensions: Optional[Sequence[str]] = None,
    ) -> IFSWatch:
        assert (
            self._initialized_event.is_set()
        ), "Initialization not completed. Unable to notify on changes."

        writer = self.writer
        if writer is None:
            raise RuntimeError(
                "Server communication is not initialized. start_server() or connect_to_server() must be called before notifying of changes."
            )

        on_change_id: str = self._next_id()
        path_args = [{"path": p.path, "recursive": p.recursive} for p in paths]

        remote_fs_watch = _RemoteFSWatch(self, on_change_id, on_change, call_args)
        self._change_id_to_fs_watch[on_change_id] = remote_fs_watch

        if extensions is not None:
            extensions = tuple(extensions)

        writer.write(
            {
                "command": "notify_on_any_change",
                "paths": path_args,
                "on_change_id": on_change_id,
                "extensions": extensions,
            }
        )
        # Wait for the command to be acknowledged...
        if not remote_fs_watch.acknowledged.wait(5):
            log.info(f"Command to notify on change not acknowledged. Paths: {paths}!")
        return remote_fs_watch

    def _on_read(self, msg):
        command = msg.get("command")

        if command == "ack_initialize":
            self._initialized_event.set()

        elif command == "ack_notify_on_any_change":
            on_change_id = msg["on_change_id"]
            remote_fs_watch: _RemoteFSWatch = self._change_id_to_fs_watch.get(
                on_change_id
            )
            if remote_fs_watch is not None:
                remote_fs_watch.acknowledged.set()
            else:
                log.info(
                    f"ack_notify_on_any_change did not find on_change_id: {on_change_id}"
                )

        elif command == "on_change":
            on_change_id = msg["on_change_id"]
            remote_fs_watch = self._change_id_to_fs_watch.get(on_change_id)
            # It may be None and that's ok (it may've been disposed in the meanwhile).
            if remote_fs_watch is not None:
                src_path = msg["src_path"]
                remote_fs_watch.on_change(src_path, *remote_fs_watch.call_args)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements
        from robocorp_ls_core.watchdog_wrapper import IFSObserver

        _: IFSObserver = check_implements(self)
