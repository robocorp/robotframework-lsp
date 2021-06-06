class RobotFrameworkFacade(object):
    """
    Nothing on Robot Framework is currently typed, so, this is a facade
    to help to deal with it so that we don't add lots of things to ignore its
    imports/typing.
    """

    @property
    def get_model(self):
        from robot.api import get_model  # type:ignore

        return get_model

    @property
    def TestSuite(self):
        from robot.api import TestSuite

        return TestSuite

    @property
    def Token(self):
        from robot.api import Token

        return Token

    @property
    def DataError(self):
        from robot.errors import DataError  # type:ignore

        return DataError

    @property
    def EXECUTION_CONTEXTS(self):
        from robot.running.context import EXECUTION_CONTEXTS  # type:ignore

        return EXECUTION_CONTEXTS

    @property
    def ErrorReporter(self):
        from robot.running.builder.parsers import ErrorReporter  # type:ignore

        return ErrorReporter

    @property
    def SettingsBuilder(self):
        from robot.running.builder.transformers import SettingsBuilder  # type:ignore

        return SettingsBuilder

    @property
    def SuiteBuilder(self):
        from robot.running.builder.transformers import SuiteBuilder  # type:ignore

        return SuiteBuilder

    @property
    def TestDefaults(self):
        from robot.running.builder.testsettings import TestDefaults  # type:ignore

        return TestDefaults
