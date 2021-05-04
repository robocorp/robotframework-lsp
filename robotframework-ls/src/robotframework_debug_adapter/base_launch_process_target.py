from __future__ import annotations

from functools import partial
import itertools
import threading
from typing import Optional, Dict
import sys

if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol

import typing
import weakref
from robotframework_debug_adapter.constants import DEBUG

from robocorp_ls_core.debug_adapter_core.dap.dap_base_schema import BaseSchema
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    TerminatedEvent,
    StoppedEvent,
)


log = get_logger(__name__)

if typing.TYPE_CHECKING:
    from robotframework_debug_adapter.debug_adapter_comm import DebugAdapterComm


class IProtocolMessageCallable(Protocol):
    def __call__(self, message: BaseSchema) -> None:
        pass


class INextSeq(Protocol):
    def __call__(self) -> int:
        pass


class BaseLaunchProcessTargetComm(threading.Thread):
    def __init__(self, debug_adapter_comm: DebugAdapterComm) -> None:
        threading.Thread.__init__(self)
        self._weak_debug_adapter_comm = weakref.ref(debug_adapter_comm)

        self._connected_event = threading.Event()

        self._process_event_msg = None
        self._process_event = threading.Event()

        self._terminated_event_msg: Optional[TerminatedEvent] = None
        self._terminated_lock = threading.Lock()
        self._terminated_event = threading.Event()
        self._next_seq: INextSeq = partial(next, itertools.count(0))
        self._msg_id_to_on_response: Dict[int, Optional[IProtocolMessageCallable]] = {}

    def _handle_received_protocol_message_from_backend(
        self, protocol_message: BaseSchema, backend: str
    ) -> None:
        from robocorp_ls_core.debug_adapter_core.debug_adapter_threads import (
            READER_THREAD_STOPPED,
        )
        import json

        if protocol_message is READER_THREAD_STOPPED:
            if DEBUG:
                log.debug(
                    f"{self.__class__.__name__} when reading from {backend}: READER_THREAD_STOPPED."
                )
            return

        if DEBUG:
            log.debug(
                "Process json: %s\n"
                % (json.dumps(protocol_message.to_dict(), indent=4, sort_keys=True),)
            )

        try:
            on_response: Optional[IProtocolMessageCallable] = None
            if protocol_message.type == "request":
                from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Request

                req = typing.cast(Request, protocol_message)
                method_name = f"on_{req.command}_request"

            elif protocol_message.type == "event":
                from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Event

                ev = typing.cast(Event, protocol_message)
                method_name = f"on_{ev.event}_event"

            elif protocol_message.type == "response":
                from robocorp_ls_core.debug_adapter_core.dap.dap_schema import Response

                resp = typing.cast(Response, protocol_message)
                on_response = self._msg_id_to_on_response.pop(resp.request_seq, None)
                method_name = f"on_{resp.command}_response"

            else:
                if DEBUG:
                    log.debug(
                        "Unable to decide how to deal with protocol type: %s (read from %s - %s).\n"
                        % (protocol_message.type, backend, self.__class__.__name__)
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
                        "Unhandled: %s not available when reading from %s - %s.\n"
                        % (method_name, backend, self.__class__.__name__)
                    )
        except:
            log.exception("Error")

    def on_stopped_event(self, event: StoppedEvent):
        debug_adapter_comm = self._weak_debug_adapter_comm()
        if debug_adapter_comm is not None:
            debug_adapter_comm.weak_stopped_target_comm = weakref.ref(self)
            debug_adapter_comm.write_to_client_message(event)
        else:
            log.debug("Command processor collected in event: %s" % (event,))
