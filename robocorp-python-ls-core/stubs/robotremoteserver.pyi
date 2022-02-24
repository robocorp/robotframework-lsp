from typing import Any, Tuple

class RobotRemoteServer:
    def __init__(
        self,
        library: Any,
        host: str = "127.0.0.1",
        port: int = 8270,
        port_file=None,
        allow_stop="DEPRECATED",
        serve: bool = True,
        allow_remote_stop: bool = True,
    ):
        pass
    @property
    def server_port(self) -> int:
        pass
    @property
    def server_address(self) -> Tuple[str, int]:
        pass
    def activate(self) -> int:
        pass
    def serve(self, log: bool = True) -> None:
        pass
    def stop(self):
        pass
