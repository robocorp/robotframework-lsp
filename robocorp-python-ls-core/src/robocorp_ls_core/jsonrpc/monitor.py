from robocorp_ls_core.jsonrpc.exceptions import JsonRpcRequestCancelled


class Monitor(object):
    def __init__(self):
        self._cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True

    def check_cancelled(self) -> None:
        if self._cancelled:
            raise JsonRpcRequestCancelled()
