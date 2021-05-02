from functools import partial
from robotframework_debug_adapter.constants import DEBUG
import itertools
import queue
import threading
import weakref
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.options import DEFAULT_TIMEOUT


log = get_logger(__name__)


class LaunchProcessDebugAdapterPydevdComm(threading.Thread):
    def __init__(self, debug_adapter_comm, server_socket):
        threading.Thread.__init__(self)
        self._server_socket = server_socket
        assert server_socket is not None

        self._connected_event = threading.Event()

        self._process_event_msg = None
        self._process_event = threading.Event()

        self._terminated_event_msg = None
        self._terminated_lock = threading.Lock()
        self._terminated_event = threading.Event()

        self._write_to_pydevd_queue = queue.Queue()
        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)

        self._next_seq = partial(next, itertools.count(0))
        self._msg_id_to_on_response = {}

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
            socket, addr = self._server_socket.accept()

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

    def _from_pydevd(self, protocol_message):
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )
        import json

        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug(
                    "%s when reading from pydevd: READER_THREAD_STOPPED."
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
                        "Unable to decide how to deal with protocol type: %s (read from pydevd - %s).\n"
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
                        "Unhandled: %s not available when reading from pydevd - %s.\n"
                        % (method_name, self.__class__.__name__)
                    )
        except:
            log.exception("Error")

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
