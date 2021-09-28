import threading
from robocorp_ls_core.robotframework_log import get_logger
from typing import Tuple, Optional

log = get_logger(__name__)

import socket as socket_module

from socket import (
    AF_INET,
    SOCK_STREAM,
    SHUT_WR,
    SOL_SOCKET,
    SO_REUSEADDR,
    IPPROTO_TCP,
    socket,
)


def create_server_socket(host, port):
    from robocorp_ls_core.constants import IS_WINDOWS

    try:
        server = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)
        if IS_WINDOWS:
            server.setsockopt(SOL_SOCKET, socket_module.SO_EXCLUSIVEADDRUSE, 1)
        else:
            server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

        server.bind((host, port))
        server.settimeout(None)
    except Exception:
        server.close()
        raise

    return server


class _ClientThread(threading.Thread):
    """
    Helper class to act as the client (it will create the initial socket to
    wait for the connection and provides the debugger_api as a helper to talk
    to the debugger through sockets).
    """

    def __init__(self) -> None:
        from robotframework_debug_adapter_tests.fixtures import _DebuggerAPI

        threading.Thread.__init__(self)
        self.name = "_ClientThread(a.k.a: Jupyter/VSCode/Eclipse)."
        self._server_socket = create_server_socket("127.0.0.1", 0)
        self._server_socket.listen(1)
        self.started = threading.Event()
        self.finish = threading.Event()
        self.sockets_closed = threading.Event()
        self.debugger_api: Optional[_DebuggerAPI] = None

    def run(self) -> None:
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            STOP_WRITER_THREAD,
        )

        socket, _addr = self._server_socket.accept()
        self._server_socket.close()

        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            writer_thread,
        )
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            reader_thread,
        )
        import queue
        from robotframework_debug_adapter_tests.fixtures import _DebuggerAPI

        read_from = socket.makefile("rb")
        write_to = socket.makefile("wb")

        write_queue: queue.Queue = queue.Queue()
        read_queue: queue.Queue = queue.Queue()

        writer = threading.Thread(
            target=writer_thread,
            args=(write_to, write_queue),
            name="Client debugger API writer",
        )
        writer.daemon = True
        reader = threading.Thread(
            target=reader_thread,
            args=(read_from, read_queue.put, read_queue),
            name="Client debugger API reader",
        )
        reader.daemon = True

        reader.start()
        writer.start()

        self.debugger_api = _DebuggerAPI(
            reader=reader,
            writer=writer,
            write_queue=write_queue,
            read_queue=read_queue,
            dap_resources_dir=None,
        )
        self.started.set()

        try:
            assert self.finish.wait(5)
            write_queue.put(STOP_WRITER_THREAD)
            socket.shutdown(SHUT_WR)
            socket.close()
        except:
            log.exception()
        finally:
            self.sockets_closed.set()

    def get_address(self) -> Tuple[str, int]:
        return self._server_socket.getsockname()


def test_debug_adapter_threaded(
    debugger_api_core, dap_log_file, robot_thread, dap_logs_dir
):
    """
    This is an example on how to setup the debugger structure in-memory but
    still talking through the DAP instead of using the core APIs.

    debugger_api_core: helper to get file to run / compute breakpoint position.
    dap_log_file: a place to store logs.
    robot_thread: helper run robot in a thread.
    dap_logs_dir: another api to store the logs needed.
    """
    import robotframework_ls
    from robotframework_debug_adapter_tests.fixtures import dbg_wait_for
    from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
        STOP_WRITER_THREAD,
    )

    robotframework_ls.import_robocorp_ls_core()

    # Configure the logger
    from robocorp_ls_core.robotframework_log import configure_logger

    reader, writer = None, None

    with configure_logger("robot", 3, dap_log_file):

        # i.e: create the server socket which will wait for the debugger connection.
        client_thread = _ClientThread()
        try:
            client_thread.start()
            address = client_thread.get_address()

            from robotframework_debug_adapter.run_robot__main__ import (
                connect,
                _RobotTargetComm,
            )

            # Note: _RobotTargetComm takes care of initializing the debugger.
            processor = _RobotTargetComm(connect(address[1]), debug=True)
            reader, writer = processor.start_communication_threads(
                mark_as_pydevd_threads=False
            )
            assert client_thread.started.wait(2)

            # Ok, at this point the setup should be done, let's set a breakpoint
            # then ask to run and see if it stops there.
            target = debugger_api_core.get_dap_case_file("case_log.robot")
            debugger_api_core.target = target
            line = debugger_api_core.get_line_index_with_content("check that log works")

            client_thread.debugger_api.set_breakpoints(target, line)

            # Actually run it (do it in a thread so that we can verify
            # things on this thread).
            robot_thread.run_target(target)

            json_hit = client_thread.debugger_api.wait_for_thread_stopped(
                file=target, line=line
            )
            client_thread.debugger_api.continue_event(json_hit.thread_id)
            dbg_wait_for(
                lambda: robot_thread.result_code is not None,
                msg="Robot execution did not finish properly.",
            )

            # Run it once more to check that the communication is still in place
            # -- i.e.: we don't actually terminate it if the connection was done
            # in memory.
            from robotframework_debug_adapter_tests.fixtures import RunRobotThread

            robot_thread2 = RunRobotThread(dap_logs_dir)
            robot_thread2.run_target(target)
            json_hit = client_thread.debugger_api.wait_for_thread_stopped(
                file=target, line=line
            )
            client_thread.debugger_api.continue_event(json_hit.thread_id)
            dbg_wait_for(
                lambda: robot_thread2.result_code is not None,
                msg="Robot execution did not finish properly.",
            )
        finally:
            # Upon finish the client should close the sockets to finish the readers.
            client_thread.finish.set()
            # Upon finish ask the writer thread to exit too (it won't automatically finish
            # even if sockets are closed).
            processor.write_message(STOP_WRITER_THREAD)

        assert client_thread.sockets_closed.wait(1)

    if reader is not None:
        reader.join(2)
        assert not reader.is_alive(), "Expected reader to have exited already."
    if writer is not None:
        writer.join(2)
        assert not writer.is_alive(), "Expected writer to have exited already."
