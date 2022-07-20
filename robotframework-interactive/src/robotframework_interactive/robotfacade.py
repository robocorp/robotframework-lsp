from typing import Sequence, Dict, Any


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
    def SettingsBuilder(self):
        from robot.running.builder.transformers import SettingsBuilder  # type:ignore

        return SettingsBuilder

    @property
    def SuiteBuilder(self):
        from robot.running.builder.transformers import SuiteBuilder  # type:ignore

        return SuiteBuilder

    @property
    def TestDefaults(self):
        try:
            # RF 5.1 onwards.
            from robot.running.builder.settings import (
                Defaults as TestDefaults,  # type:ignore
            )
        except ImportError:
            from robot.running.builder.testsettings import TestDefaults  # type:ignore

        return TestDefaults

    def get_libraries_imported_in_namespace(self):
        EXECUTION_CONTEXTS = self.EXECUTION_CONTEXTS
        return set(EXECUTION_CONTEXTS.current.namespace._kw_store.libraries)

    def run_test_body(self, context, test):
        from robot import version

        IS_ROBOT_4_ONWARDS = not version.get_version().startswith("3.")
        if IS_ROBOT_4_ONWARDS:
            from robot.running.bodyrunner import BodyRunner  # noqa

            BodyRunner(context, templated=False).run(test.body)
        else:
            from robot.running.steprunner import StepRunner  # noqa

            StepRunner(context, False).run_steps(test.keywords.normal)

    @property
    def EmbeddedArgumentsHandler(self):
        from robot.running.userkeyword import EmbeddedArgumentsHandler  # type:ignore

        return EmbeddedArgumentsHandler

    def parse_arguments_options(self, arguments: Sequence[str]) -> Dict[str, Any]:
        from robot.run import RobotFramework  # type:ignore

        arguments = list(arguments)

        # Add the target as an arg (which is to be ignored as
        # we just want the options in this API).
        arguments.append("<ignore>")

        opts, _ = RobotFramework().parse_arguments(
            arguments,
        )
        return opts
