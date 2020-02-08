from robotframework_ls.jsonrpc.dispatchers import MethodDispatcher
import logging


log = logging.getLogger(__name__)


class RobotFrameworkServerApi(MethodDispatcher):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(self, read_from, write_to):
        from robotframework_ls.jsonrpc.streams import (
            JsonRpcStreamReader,
            JsonRpcStreamWriter,
        )
        from robotframework_ls.jsonrpc.endpoint import Endpoint

        self._version = None
        self._jsonrpc_stream_reader = JsonRpcStreamReader(read_from)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(write_to)
        self._endpoint = Endpoint(
            self, self._jsonrpc_stream_writer.write, max_workers=1
        )

    def start(self):
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def m_initialize(self, processId=None, **_kwargs):
        if processId not in (None, -1, 0):
            from robotframework_ls._utils import exit_when_pid_exists

            exit_when_pid_exists(processId)

    def m_version(self):
        if self._version is not None:
            return self._version
        try:
            from robot import get_version

            version = get_version(naked=True)
        except:
            log.exception("Unable to get version.")
            version = "N/A"  # Too old?
        self._version = version
        return self._version

    def _check_min_version(self, min_version):
        from robotframework_ls._utils import check_min_version

        version = self.m_version()
        return check_min_version(version, min_version)

    def m_lint(self, source=None):
        if not source:
            return []

        if not self._check_min_version((3, 2)):
            from robotframework_ls.server_api.errors import Error

            msg = (
                "robotframework version (%s) too old for linting.\n"
                "Please install a newer version and restart the language server."
                % (self.m_version(),)
            )
            log.info(msg)
            return [Error(msg, (0, 0), (1, 0)).to_lsp_diagnostic()]

        try:
            from robotframework_ls.server_api.errors import collect_errors

            errors = collect_errors(source)
            return [error.to_lsp_diagnostic() for error in errors]
        except:
            log.exception("Error collecting errors.")
            return []

    def m_shutdown(self, **_kwargs):
        pass

    def m_exit(self, **_kwargs):
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()
