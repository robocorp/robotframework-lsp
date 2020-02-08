from robotframework_ls.client_base import LanguageServerClientBase


class SubprocessDiedError(Exception):
    pass


class RobotFrameworkApiClient(LanguageServerClientBase):
    def __init__(self, writer, reader, server_process):
        LanguageServerClientBase.__init__(self, writer, reader)
        self.server_process = server_process
        self._check_process_alive()

    def _check_process_alive(self, raise_exception=True):
        if self.server_process.returncode is not None:
            if raise_exception:
                raise SubprocessDiedError(
                    "Process has already exited. Stderr: %s"
                    % (self.server_process.stderr.read())
                )
            return False
        return True

    def initialize(self, msg_id=None, process_id=None):
        self._check_process_alive()
        msg_id = msg_id if msg_id is not None else self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "initialize",
                "params": {"processId": process_id},
            },
            timeout=3,
        )

    def get_version(self):
        """
        :return:
        """
        self._check_process_alive()
        msg_id = self.next_id()
        msg = self.request({"jsonrpc": "2.0", "id": msg_id, "method": "version"})

        version = msg.get("result", "N/A")
        return version

    def lint(self, source):
        self._check_process_alive()
        msg_id = self.next_id()
        return self.request(
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "lint",
                "params": {"source": source},
            }
        )
