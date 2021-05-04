from __future__ import annotations

import queue
import threading
from typing import Optional
import typing

from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import BaseSchema
from robocorp_ls_core.options import DEFAULT_TIMEOUT
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.base_launch_process_target import (
    BaseLaunchProcessTargetComm,
    IProtocolMessageCallable,
)


if typing.TYPE_CHECKING:
    from robotframework_debug_adapter.debug_adapter_comm import DebugAdapterComm

log = get_logger(__name__)


class LaunchProcessDebugAdapterPydevdComm(BaseLaunchProcessTargetComm):
    def __init__(self, debug_adapter_comm: DebugAdapterComm, server_socket):
        BaseLaunchProcessTargetComm.__init__(self, debug_adapter_comm)
        self._server_socket = server_socket
        assert server_socket is not None
        self._write_to_pydevd_queue: "queue.Queue[BaseSchema]" = queue.Queue()

    def run(self):
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            writer_thread_no_auto_seq,
        )
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            reader_thread,
        )

        try:

            # while True:
            # Only handle a single connection...
            socket, _addr = self._server_socket.accept()

            read_from = socket.makefile("rb")
            write_to = socket.makefile("wb")

            debug_adapter_comm = self._weak_debug_adapter_comm()
            writer = self._writer_thread = threading.Thread(
                target=writer_thread_no_auto_seq,
                args=(write_to, self._write_to_pydevd_queue, "write to pydevd process"),
                name="Write to pydevd (LaunchProcessDebugAdapterPydevdComm)",
            )
            writer.daemon = True

            reader = self._reader_thread = threading.Thread(
                target=reader_thread,
                args=(
                    read_from,
                    self._from_pydevd,
                    debug_adapter_comm.write_to_client_queue,  # Used for errors
                    b"read from pydevd process",
                ),
                name="Read from pydevd (LaunchProcessDebugAdapterPydevdComm)",
            )
            reader.daemon = True

            reader.start()
            writer.start()

            self._connected_event.set()
        except:
            log.exception()

    def _from_pydevd(self, protocol_message: BaseSchema) -> None:
        self._handle_received_protocol_message_from_backend(protocol_message, "pydevd")

    def write_to_pydevd_message(
        self, protocol_message, on_response: Optional[IProtocolMessageCallable] = None
    ):
        """
        :param BaseSchema protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        seq = protocol_message.seq = self._next_seq()
        if on_response is not None:
            self._msg_id_to_on_response[seq] = on_response
        self._write_to_pydevd_queue.put(protocol_message)

    def wait_for_connection(self):
        """
        :return bool:
            Returns True if the connection was successful and False otherwise.
        """
        assert self.is_alive() is not None, "start() must be called first."
        log.debug("Wating for connection for %s seconds." % (DEFAULT_TIMEOUT,))
        ret = self._connected_event.wait(DEFAULT_TIMEOUT)
        log.debug("Connected: %s" % (ret,))
        return ret
