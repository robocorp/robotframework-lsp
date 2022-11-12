from __future__ import annotations

import os
import queue
import threading
import typing

from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import BaseSchema
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    TerminatedEvent,
    TerminatedEventBody,
    Event,
)
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.base_launch_process_target import (
    BaseLaunchProcessTargetComm,
)
from robotframework_ls.options import DEFAULT_TIMEOUT
from typing import Optional


if typing.TYPE_CHECKING:
    from robotframework_debug_adapter.debug_adapter_comm import DebugAdapterComm


log = get_logger(__name__)


class LaunchProcessDebugAdapterRobotTargetComm(BaseLaunchProcessTargetComm):
    """
    This class is used so intermediate talking to the server.

    It's the middle ground between the `DebugAdapterComm` and `_RobotTargetComm`.
        - `DebugAdapterComm`:
            It's used to talk with the client (in this process) and accessed
            through the _weak_debug_adapter_comm attribute.

        - `_RobotTargetComm`
            It's actually in the target process. We communicate with it by
            calling the `write_to_robot_message` method and receive messages
            from it in the `_from_robot` method in this class.
    """

    def __init__(self, debug_adapter_comm: DebugAdapterComm):
        BaseLaunchProcessTargetComm.__init__(self, debug_adapter_comm)

        self._server_socket = None

        self._write_to_robot_queue: "queue.Queue[BaseSchema]" = queue.Queue()

    def start_listening(self, connections_count):
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        # i.e. 2 connections accepted: robot target and pydevd (or only robot
        # if not in debug mode).
        s.listen(connections_count)
        self._server_socket = s
        self.start()
        return port, s

    def run(self):
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            writer_thread_no_auto_seq,
        )
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            reader_thread,
        )

        try:
            assert (
                self._server_socket is not None
            ), "start_listening must be called before start()"

            # while True:
            # Only handle a single connection...
            socket, _addr = self._server_socket.accept()

            read_from = socket.makefile("rb")
            write_to = socket.makefile("wb")

            debug_adapter_comm = self._weak_debug_adapter_comm()
            writer = self._writer_thread = threading.Thread(
                target=writer_thread_no_auto_seq,
                args=(write_to, self._write_to_robot_queue, "write to robot process"),
                name="Write to robot (LaunchProcessDebugAdapterRobotTargetComm)",
            )
            writer.daemon = True

            reader = self._reader_thread = threading.Thread(
                target=reader_thread,
                args=(
                    read_from,
                    self._from_robot,
                    debug_adapter_comm.write_to_client_queue,  # Used for errors
                    b"read from robot process",
                ),
                name="Read from robot (LaunchProcessDebugAdapterRobotTargetComm)",
            )
            reader.daemon = True

            reader.start()
            writer.start()

            self._connected_event.set()
        except:
            log.exception()

    def _from_robot(self, protocol_message: BaseSchema) -> None:
        self._handle_received_protocol_message_from_backend(protocol_message, "robot")

    def on_process_event(self, event):
        self._process_event_msg = event
        self._process_event.set()

        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            event.body.kwargs["dapProcessId"] = os.getpid()
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    def get_pid(self):
        assert self._process_event.is_set()
        return self._process_event_msg.body.systemProcessId

    def _forward_event_to_client(self, event: Event) -> None:
        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    on_output_event = _forward_event_to_client

    on_startSuite_event = _forward_event_to_client
    on_endSuite_event = _forward_event_to_client

    on_startTest_event = _forward_event_to_client
    on_endTest_event = _forward_event_to_client

    on_logMessage_event = _forward_event_to_client

    on_rfStream_event = _forward_event_to_client

    def is_terminated(self):
        with self._terminated_lock:
            return self._terminated_event.is_set()

    def on_terminated_event(self, event: Optional[TerminatedEvent]) -> None:
        with self._terminated_lock:
            if self._terminated_event.is_set():
                return

            if event is None:
                restart = False
                event = TerminatedEvent(body=TerminatedEventBody(restart=restart))

            self._terminated_event_msg = event
            self._terminated_event.set()

        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    def notify_exit(self) -> None:
        self.on_terminated_event(None)
        log.debug("Target process finished (forcibly exiting debug adapter in 100ms).")

        # If the target process is terminated, wait a bit and exit ourselves.
        import time

        time.sleep(0.1)
        os._exit(0)

    def write_to_robot_message(
        self, protocol_message: BaseSchema, on_response=None
    ) -> None:
        """
        :param BaseSchema protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        seq: int = self._next_seq()
        protocol_message.seq = seq
        if on_response is not None:
            self._msg_id_to_on_response[seq] = on_response
        self._write_to_robot_queue.put(protocol_message)

    def wait_for_connection(self):
        """
        :return bool:
            Returns True if the connection was successful and False otherwise.
        """
        assert self._server_socket is not None, "start_listening must be called first."
        log.debug("Wating for connection for %s seconds." % (DEFAULT_TIMEOUT,))
        ret = self._connected_event.wait(DEFAULT_TIMEOUT)
        log.debug("Connected: %s" % (ret,))
        return ret

    def wait_for_process_event(self):
        log.debug("Wating for process event for %s seconds." % (DEFAULT_TIMEOUT,))
        ret = self._process_event.wait(DEFAULT_TIMEOUT)
        log.debug("Received process event: %s" % (ret,))
        return ret
