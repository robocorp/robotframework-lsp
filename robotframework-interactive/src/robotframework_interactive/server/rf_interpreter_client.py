from robocorp_ls_core.client_base import LanguageServerClientBase
from robocorp_ls_core.protocols import ActionResultDict
from robocorp_ls_core.options import DEFAULT_TIMEOUT
from typing import Any, Dict, Optional


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
        self._waiting_input = 0

    def _on_received_message(self, msg):
        if isinstance(msg, dict):
            method = msg.get("method")
            if method == "interpreter/output":
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

            elif method == "interpreter/beforeRead":
                self._waiting_input += 1

            elif method == "interpreter/afterRead":
                self._waiting_input -= 1

    @property
    def waiting_input(self):
        return bool(self._waiting_input)

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

    def interpreter_start(
        self, uri: str, settings: Dict[str, Any], workspace_root_path: Optional[str]
    ) -> ActionResultDict:
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "interpreter/start",
                    "params": {
                        "uri": uri,
                        "settings": settings,
                        "workspace_root_path": workspace_root_path,
                    },
                },
                timeout=None,
            )
        )

    def interpreter_evaluate(self, code: str) -> ActionResultDict:
        self._check_process_alive()
        if self._waiting_input:
            self.server_process.stdin.write(code.encode("utf-8", errors="replace"))
            if not code.endswith(("\r", "\n")):
                self.server_process.stdin.write(b"\n")
            self.server_process.stdin.flush()
            return {"success": True, "message": None, "result": None}

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

    def interpreter_compute_evaluate_text(
        self, code: str, target_type: str = "evaluate"
    ) -> ActionResultDict:
        """
        :param target_type:
            'evaluate': means that the target is an evaluation with the given code.
                This implies that the current code must be changed to make sense
                in the given context.

            'completions': means that the target is a code-completion
                This implies that the current code must be changed to include
                all previous successful evaluations so that the code-completion
                contains the full information up to the current point.
        """
        self._check_process_alive()
        msg_id = self.next_id()
        return self._unpack_result_as_action_result_dict(
            self.request(
                {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "method": "interpreter/computeEvaluateText",
                    "params": {"code": code, "target_type": target_type},
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
                timeout=DEFAULT_TIMEOUT,
            )
        )
