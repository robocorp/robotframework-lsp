import sys
from typing import Dict, Optional, Union

from robocorp_ls_core.basic import implements
from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import (
    IErrorMessage,
    IIdMessageMatcher,
    ILanguageServerClientBase,
    IResultMessage,
)

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass

    class TypedDict(object):
        def __init_subclass__(self, *args, **kwargs):
            pass

else:
    from typing import Protocol, TypedDict


class SubprocessDiedError(Exception):
    pass


class InspectorApiClient(LanguageServerClientBase):
    def __init__(
        self, writer, reader, server_process, on_received_message=None
    ) -> None:
        LanguageServerClientBase.__init__(
            self, writer, reader, on_received_message=on_received_message
        )
        self.server_process = server_process
        self._check_process_alive()
        self._version = None

        self.stats: Dict[str, int] = {}

    @implements(ILanguageServerClientBase.write)
    def write(self, contents):
        if isinstance(contents, dict):
            method = contents.get("method")
            if method:
                self.stats[method] = self.stats.get(method, 0) + 1
        return LanguageServerClientBase.write(self, contents)

    def _check_process_alive(self, raise_exception=True):
        returncode = self.server_process.poll()
        if returncode is not None:
            if raise_exception:
                raise SubprocessDiedError(
                    "Process has already exited. Stderr: %s"
                    % (self.server_process.stderr.read())
                )
            return False
        return True

    def initialize(self, process_id=None):
        from robocorp_ls_core.options import NO_TIMEOUT, USE_TIMEOUTS

        self._check_process_alive()
        msg_id = self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {
                    "processId": process_id,
                },
            },
            timeout=30 if USE_TIMEOUTS else NO_TIMEOUT,
        )

    def _build_msg(self, method_name, params):
        self._check_process_alive()
        msg_id = self.next_id()
        return {"jsonrpc": "2.0", "id": msg_id, "method": method_name, "params": params}

    ###### Message Handlers

    def send_sync_message(
        self, method_name, params: dict
    ) -> Optional[Union[IResultMessage, IErrorMessage]]:
        self._check_process_alive()
        return self.request(self._build_msg(method_name, params))

    def send_async_message(
        self, method_name, params: dict
    ) -> Optional[IIdMessageMatcher]:
        """
        :Note: async complete.
        """
        return self.request_async(self._build_msg(method_name, params))

    def request_cancel(self, message_id):
        self._check_process_alive()
        self.write(
            {
                "jsonrpc": "2.0",
                "method": "$/cancelRequest",
                "params": dict(id=message_id),
            }
        )
