class RobotFrameworkDebugAdapter:
    ROBOT_LISTENER_API_VERSION = 3

    def end_test(self, data, result) -> None:
        print("end test")


class RFDebugAdapter:
    ROBOT_LIBRARY_LISTENER = [RobotFrameworkDebugAdapter()]

    def debug_listen(self, host: str = "127.0.0.1", port: int = 4352):
        """
        Start the debugger and listen at the given port.

        Afterwards clients are expected to create a launch configuration to
        attach.
        """
        assert isinstance(host, str), "Expected host to be a string"
        assert isinstance(port, int), "Expected port to be an int"
        print("dbg listen")
