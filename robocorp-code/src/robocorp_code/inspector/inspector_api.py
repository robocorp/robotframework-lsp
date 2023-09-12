from robocorp_ls_core.basic import overrides
from robocorp_ls_core.protocols import IConfig
from robocorp_ls_core.python_ls import PythonLanguageServer


class InspectorApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(
        self,
        read_from,
        write_to,
    ):
        PythonLanguageServer.__init__(self, read_from, write_to)

    def _create_config(self) -> IConfig:
        from robocorp_code.robocorp_config import RobocorpConfig

        return RobocorpConfig()

    @overrides(PythonLanguageServer.lint)
    def lint(self, *args, **kwargs):
        pass  # No-op for this server.

    @overrides(PythonLanguageServer.cancel_lint)
    def cancel_lint(self, *args, **kwargs):
        pass  # No-op for this server.

    def m_echo(self, arg):
        return "echo", arg
