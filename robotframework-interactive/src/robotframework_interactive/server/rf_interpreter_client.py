from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import ActionResultDict


class SubprocessDiedError(Exception):
    pass


class RfInterpreterApiClient(LanguageServerClientBase):
    def __init__(self, writer, reader, server_process, on_interpreter_message=None):
        LanguageServerClientBase.__init__(
            self, writer, reader, on_received_message=self._on_received_message
        )
        self.server_process = server_process
        self._check_process_alive()
        self._version = None
        self._on_interpreter_message = on_interpreter_message

    def _on_received_message(self, msg):
        if isinstance(msg, dict):
            if msg.get("method") == "interpreter/output":
                # Something as:
                # {
                #     "jsonrpc": "2.0",
                #     "method": "interpreter/output",
                #     "params": {
                #         "output": "Some output\n",
                #         "category": "stdout",
                #     },
                # }
                on_interpreter_message = self._on_interpreter_message
                if on_interpreter_message is not None:
                    on_interpreter_message(msg)

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
        if not isinstance(result, dict):
            return {"success": False, "message": str(result), "result": None}

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

    def interpreter_start(self) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "interpreter/start",
                    "params": {},
                },
                timeout=None,
            )
        )

    def interpreter_evaluate(self, code: str) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "interpreter/evaluate",
                    "params": {"code": code},
                },
                timeout=None,
            )
        )

    def interpreter_stop(self) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "interpreter/stop",
                    "params": {},
                },
                timeout=None,
            )
        )
