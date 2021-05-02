from functools import partial
import itertools
import json
import os
import queue
import threading

from robocorp_ls_core.robotframework_log import get_logger
from robotframework_debug_adapter.constants import DEBUG
from robotframework_ls.options import DEFAULT_TIMEOUT


log = get_logger(__name__)


class LaunchProcessDebugAdapterRobotTargetComm(threading.Thread):
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

    def __init__(self, debug_adapter_comm):
        threading.Thread.__init__(self)
        import weakref

        self._server_socket = None
        self._connected_event = threading.Event()

        self._process_event_msg = None
        self._process_event = threading.Event()

        self._terminated_event_msg = None
        self._terminated_lock = threading.Lock()
        self._terminated_event = threading.Event()

        self._write_to_robot_queue = queue.Queue()
        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)

        self._next_seq = partial(next, itertools.count(0))
        self._msg_id_to_on_response = {}

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
            socket, addr = self._server_socket.accept()

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

    def _from_robot(self, protocol_message):
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )

        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug(
                    "%s when reading from robot: READER_THREAD_STOPPED."
                    % (self.__class__.__name__,)
                )
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        try:
            on_response = None
            if protocol_message.type == "request":
                method_name = "on_%s_request" % (protocol_message.command,)
            elif protocol_message.type == "event":
                method_name = "on_%s_event" % (protocol_message.event,)
            elif protocol_message.type == "response":
                on_response = self._msg_id_to_on_response.pop(
                    protocol_message.request_seq, None
                )
                method_name = "on_%s_response" % (protocol_message.command,)
            else:
                if DEBUG:
                    log.debug(
                        "Unable to decide how to deal with protocol type: %s (read from robot - %s).\n"
                        % (protocol_message.type, self.__class__.__name__)
                    )
                return

            if on_response is not None:
                on_response(protocol_message)

            on_request = getattr(self, method_name, None)

            if on_request is not None:
                on_request(protocol_message)
            elif on_response is not None:
                pass
            else:
                if DEBUG:
                    log.debug(
                        "Unhandled: %s not available when reading from robot - %s.\n"
                        % (method_name, self.__class__.__name__)
                    )
        except:
            log.exception("Error")

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

    def on_stopped_event(self, event):
        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    def on_terminated_event(self, event):
        with self._terminated_lock:
            if self._terminated_event.is_set():
                return

            if event is None:
                from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
                    TerminatedEvent,
                )
                from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
                    TerminatedEventBody,
                )

                restart = False
                event = TerminatedEvent(body=TerminatedEventBody(restart=restart))

            self._terminated_event_msg = event
            self._terminated_event.set()

        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))

    def notify_exit(self):
        self.on_terminated_event(None)
        log.debug("Target process finished (forcibly exiting debug adapter in 100ms).")

        # If the target process is terminated, wait a bit and exit ourselves.
        import time

        time.sleep(0.1)
        os._exit(0)

    def write_to_robot_message(self, protocol_message, on_response=None):
        """
        :param BaseSchema protocol_message:
            Some instance of one of the messages in the debug_adapter.schema.
        """
        seq = protocol_message.seq = self._next_seq()
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
