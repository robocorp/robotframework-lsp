from pyls_jsonrpc.dispatchers import MethodDispatcher
import logging

log = logging.getLogger(__name__)


class RobotFrameworkServerApi(MethodDispatcher):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(self, rx, tx):
        from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter
        from pyls_jsonrpc.endpoint import Endpoint

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
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
        try:
            from robot import get_version

            return get_version(naked=True)
        except:
            log.exception("Unable to get version.")
            return "N/A"  # Too old?

    def m_lint(self, source=None):
        if not source:
            return []
        from robotframework_ls.server_api.errors import collect_errors

        errors = collect_errors(source)
        return [error.to_lsp_diagnostic() for error in errors]

    def m_shutdown(self, **_kwargs):
        pass

    def m_exit(self, **_kwargs):
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()
