# Original work Copyright 2018 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import uuid

from robocorp_ls_core.robotframework_log import get_logger

from .exceptions import (
    JsonRpcException,
    JsonRpcRequestCancelled,
    JsonRpcInternalError,
    JsonRpcMethodNotFound,
)


from concurrent import futures
from robocorp_ls_core.basic import implements
from robocorp_ls_core.protocols import IEndPoint, IFuture, IMonitor
from typing import Optional

log = get_logger(__name__)
JSONRPC_VERSION = "2.0"
CANCEL_METHOD = "$/cancelRequest"

FORCE_NON_THREADED_VERSION = False


def require_monitor(func):
    """
    To be used as a decorator.
    """
    func.__require_monitor__ = True
    return func


class Endpoint(object):

    SHOW_THREAD_DUMP_AFTER_TIMEOUT = 8

    def __init__(self, dispatcher, consumer, id_generator=lambda: str(uuid.uuid4())):
        """A JSON RPC endpoint for managing messages sent to/from the client.

        Args:
            dispatcher (dict): A dictionary of method name to handler function.
                The handler functions should return either the result or a callable that will be used to asynchronously
                compute the result.
            consumer (fn): A function that consumes JSON RPC message dicts and sends them to the client.
            id_generator (fn, optional): A function used to generate request IDs.
                Defaults to the string value of :func:`uuid.uuid4`.
            max_workers (int, optional): The number of workers in the asynchronous executor pool.
        """
        import os

        self._dispatcher = dispatcher
        self._consumer = consumer
        self._id_generator = id_generator

        self._client_request_futures = {}
        self._server_request_futures = {}

        # i.e.: 5 to 15 workers.
        max_workers = min(15, (os.cpu_count() or 1) + 4)
        self._executor_service = futures.ThreadPoolExecutor(max_workers=max_workers)

    def shutdown(self):
        self._executor_service.shutdown(wait=False)

    @implements(IEndPoint.notify)
    def notify(self, method: str, params=None):
        log.debug("Sending notification: %s %s", method, params)

        message = {"jsonrpc": JSONRPC_VERSION, "method": method}
        if params is not None:
            message["params"] = params

        self._consumer(message)

    @implements(IEndPoint.request)
    def request(self, method: str, params=None) -> IFuture:
        msg_id = self._id_generator()
        log.debug("Sending request with id %s: %s %s", msg_id, method, params)

        message = {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "method": method}
        if params is not None:
            message["params"] = params

        request_future: IFuture = futures.Future()
        request_future.add_done_callback(self._cancel_callback(msg_id))

        self._server_request_futures[msg_id] = request_future
        self._consumer(message)

        return request_future

    def _cancel_callback(self, request_id):
        """Construct a cancellation callback for the given request ID."""

        def callback(future):
            if future.cancelled():
                raise AssertionError(
                    "Futures should not be cancelled. Use future.set_exception(JsonRpcRequestCancelled()) instead."
                )

            exc = future.exception()
            if isinstance(exc, JsonRpcRequestCancelled):
                self.notify(CANCEL_METHOD, {"id": request_id})

        return callback

    @implements(IEndPoint.consume)
    def consume(self, message):
        if "jsonrpc" not in message or message["jsonrpc"] != JSONRPC_VERSION:
            log.warning("Unknown message type %s", message)
            return

        if "id" not in message:
            log.debug("Handling notification from client %s", message)
            self._handle_notification(message["method"], message.get("params"))
        elif "method" not in message:
            log.debug("Handling response from client %s", message)
            self._handle_response(
                message["id"], message.get("result"), message.get("error")
            )
        else:
            try:
                log.debug("Handling request from client %s", message)
                self._handle_request(
                    message["id"], message["method"], message.get("params")
                )
            except JsonRpcException as e:
                log.exception("Failed to handle request %s", message["id"])
                self._consumer(
                    {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": message["id"],
                        "error": e.to_dict(),
                    }
                )
            except Exception:  # pylint: disable=broad-except
                log.exception("Failed to handle request %s", message["id"])
                self._consumer(
                    {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": message["id"],
                        "error": JsonRpcInternalError.of(sys.exc_info()).to_dict(),
                    }
                )

    def _handle_notification(self, method, params):
        """Handle a notification from the client."""
        if method == CANCEL_METHOD:
            self._handle_cancel_notification(params["id"])
            return

        try:
            handler = self._dispatcher[method]
        except KeyError:
            log.warning("Ignoring notification for unknown method %s", method)
            return

        try:
            handler_result = handler(params)
        except Exception:  # pylint: disable=broad-except
            log.exception("Failed to handle notification %s: %s", method, params)
            return

        if callable(handler_result):
            log.debug("Executing async notification handler %s", handler_result)
            notification_future = self._executor_service.submit(handler_result)
            notification_future.add_done_callback(
                self._notification_callback(method, params)
            )

    @staticmethod
    def _notification_callback(method, params):
        """Construct a notification callback for the given request ID."""

        def callback(future):
            try:
                future.result()
                log.debug(
                    "Successfully handled async notification %s %s", method, params
                )
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    "Failed to handle async notification %s %s", method, params
                )

        return callback

    def _handle_cancel_notification(self, msg_id):
        """Handle a cancel notification from the client."""
        request_future = self._client_request_futures.pop(msg_id, None)

        if not request_future:
            log.warning(
                "Received cancel notification for unknown message id %s", msg_id
            )
            return

        # Will only work if the request hasn't started executing
        monitor: Optional[IMonitor] = getattr(request_future, "__monitor__", None)
        if monitor is not None:
            monitor.cancel()
        if request_future.cancel():
            log.debug("Cancelled request with id %s", msg_id)

    def _call_checking_time(self, func, **kwargs):
        from robocorp_ls_core import timeouts
        import threading
        import traceback

        timeout_tracker = timeouts.TimeoutTracker.get_singleton()
        curr_thread = threading.current_thread()
        timeout = self.SHOW_THREAD_DUMP_AFTER_TIMEOUT

        def on_timeout(*args, **kwargs):
            stack_trace = [
                "===============================================================================",
                f"Slow request (already took: {timeout}s). Showing thread dump.",
                "================================= Thread Dump =================================",
            ]

            for thread_id, stack in sys._current_frames().items():
                if thread_id != curr_thread.ident:
                    continue
                stack_trace.append(
                    "\n-------------------------------------------------------------------------------"
                )
                stack_trace.append(f" Thread {curr_thread}")
                stack_trace.append("")

                if "self" in stack.f_locals:
                    stack_trace.append(f"self: {stack.f_locals['self']}\n")

                for filename, lineno, name, line in traceback.extract_stack(stack):
                    stack_trace.append(
                        ' File "%s", line %d, in %s' % (filename, lineno, name)
                    )
                    if line:
                        stack_trace.append("   %s" % (line.strip()))
            stack_trace.append(
                "\n=============================== END Thread Dump ==============================="
            )
            log.critical("\n".join(stack_trace))

        if timeout > 0:
            with timeout_tracker.call_on_timeout(timeout, on_timeout, kwargs):
                return func(**kwargs)
        else:
            return func(**kwargs)

    def _handle_request(self, msg_id, method, params):
        """Handle a request from the client."""
        import time

        initial_time = time.time()
        try:
            handler = self._dispatcher[method]
        except KeyError:
            raise JsonRpcMethodNotFound.of(method)

        handler_result = handler(params)

        if callable(handler_result):
            kwargs = {}
            monitor = None
            if getattr(handler_result, "__require_monitor__", False):
                from robocorp_ls_core.jsonrpc.monitor import Monitor

                monitor = Monitor(f"Message: id: {msg_id}, method: {method}")
                kwargs["monitor"] = monitor
            log.debug("Executing async request handler %s", handler_result)

            if FORCE_NON_THREADED_VERSION:
                # I.e.: non-threaded version without breaking api.
                handler_result = handler_result(**kwargs)
                log.debug(
                    "Got result from synchronous request handler (in %.2fs): %s",
                    time.time() - initial_time,
                    handler_result,
                )
                self._consumer(
                    {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "result": handler_result}
                )

            else:
                request_future = self._executor_service.submit(
                    self._call_checking_time, handler_result, **kwargs
                )
                if monitor is not None:
                    request_future.__monitor__ = monitor
                self._client_request_futures[msg_id] = request_future
                request_future.add_done_callback(self._request_callback(msg_id))
        elif isinstance(handler_result, futures.Future):
            log.debug("Request handler is already a future %s", handler_result)
            self._client_request_futures[msg_id] = handler_result
            handler_result.add_done_callback(self._request_callback(msg_id))
        else:
            log.debug(
                "Got result from synchronous request handler (in %.2fs): %s",
                time.time() - initial_time,
                handler_result,
            )
            self._consumer(
                {"jsonrpc": JSONRPC_VERSION, "id": msg_id, "result": handler_result}
            )

    def _request_callback(self, request_id):
        """Construct a request callback for the given request ID."""

        def callback(future):
            # Remove the future from the client requests map
            self._client_request_futures.pop(request_id, None)

            try:
                message = {"jsonrpc": JSONRPC_VERSION, "id": request_id}

                if future.cancelled():
                    raise JsonRpcRequestCancelled()

                message["result"] = future.result()
            except JsonRpcRequestCancelled as e:
                log.debug("Cancelled request: %s", request_id)
                message["error"] = e.to_dict()
            except JsonRpcException as e:
                log.exception("Failed to handle request %s", request_id)
                message["error"] = e.to_dict()
            except Exception:  # pylint: disable=broad-except
                log.exception("Failed to handle request %s", request_id)
                message["error"] = JsonRpcInternalError.of(sys.exc_info()).to_dict()

            self._consumer(message)

        return callback

    def _handle_response(self, msg_id, result=None, error=None):
        """Handle a response from the client."""
        request_future = self._server_request_futures.pop(msg_id, None)

        if not request_future:
            log.warning("Received response to unknown message id %s", msg_id)
            return

        if error is not None:
            log.debug("Received error response to message %s: %s", msg_id, error)
            request_future.set_exception(JsonRpcException.from_dict(error))
        else:
            log.debug("Received result for message %s: %s", msg_id, result)
            request_future.set_result(result)
