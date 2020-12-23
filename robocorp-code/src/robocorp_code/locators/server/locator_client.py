from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_code.protocols import ActionResultDict


class SubprocessDiedError(Exception):
    pass


class LocatorsApiClient(LanguageServerClientBase):
    def __init__(self, writer, reader, server_process):
        LanguageServerClientBase.__init__(self, writer, reader)
        self.server_process = server_process
        self._check_process_alive()
        self._version = None

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

    def initialize(self, msg_id=None, process_id=None):
        from robocorp_ls_core.options import NO_TIMEOUT, USE_TIMEOUTS

        self._check_process_alive()
        msg_id = msg_id if msg_id is not None else self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {"processId": process_id},
            },
            timeout=30 if USE_TIMEOUTS else NO_TIMEOUT,
        )

    def _unpack_result_as_action_result_dict(self, result) -> ActionResultDict:
        if "result" in result:
            return result["result"]
        else:
            if "error" in result:
                error = result["error"]
                if isinstance(error, dict):
                    if "message" in error:
                        return {
                            "success": False,
                            "message": error["message"],
                            "result": None,
                        }

                return {"success": False, "message": str(error), "result": None}
            return {"success": False, "message": str(result), "result": None}

    def browser_locator_start(self, headless=False) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "browserLocator/start",
                    "params": {"headless": headless},
                },
                None,
            )
        )

    def browser_locator_stop(self) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {"jsonrpc": "2.0", "id": msg_id, "method": "browserLocator/stop"}, None
            )
        )

    def browser_locator_pick(self) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {"jsonrpc": "2.0", "id": msg_id, "method": "browserLocator/pick"}, None
            )
        )

    def image_locator_pick(self) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {"jsonrpc": "2.0", "id": msg_id, "method": "imageLocator/pick"}, None
            )
        )
