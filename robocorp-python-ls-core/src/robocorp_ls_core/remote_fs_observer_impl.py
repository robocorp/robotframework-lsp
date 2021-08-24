import itertools
import socket as socket_module
import sys
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
        on_change_id: int,
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

        self._next_id: partial[int] = partial(next, itertools.count())
        self._change_id_to_fs_watch: Dict[int, _RemoteFSWatch] = {}

        self._socket: Optional[socket_module.socket] = None
        self._backend = backend
        self._extensions = extensions
        self._initialized_event = threading.Event()

    def start_server(self, log_file: Optional[str] = None) -> int:
        """
        :return int:
            The port used by the server (which may later be used to connect
            from another observer through connect_to_server).
        """
        assert self.port is None, "RemoteFSObserver already initialized."
        import subprocess
        from robocorp_ls_core import remote_fs_observer__main__
        import time

        args = [sys.executable, "-u", remote_fs_observer__main__.__file__]
        if log_file:
            args.append(f"--log-file={log_file}")
            args.append(f"-vv")
        process = self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            bufsize=0,
        )
        stdout = process.stdout
        assert stdout
        contents = stdout.readline().strip()

        def read_fs_observer_stderr():
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                line = line.decode("utf-8", "replace")
                sys.stderr.write(line)
                log.info("Remote FS observer stderr: %s", line)

        t = threading.Thread(target=read_fs_observer_stderr)
        t.daemon = True
        t.start()

        if not contents.startswith(b"port:"):
            # Just give some time for the stderr contents to appear.
            time.sleep(0.15)
            raise AssertionError(
                f'Expected the read contents from Remote FS Observer to start with "port:". Found: {contents!r}'
            )
        contents = contents[5:].strip()

        port = int(contents)
        self.port = port
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

        on_change_id: int = self._next_id()
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
            log.info("Command to notify on change not acknowledged!")
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
