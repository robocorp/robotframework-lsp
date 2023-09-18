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
        # This is the 2nd argument to SettingsBuilder or SuiteBuilder.
        try:
            try:
                from robot.running.builder.settings import FileSettings

                return FileSettings
            except ImportError:
                pass

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

    def run_test_body(self, context, test, model):
        assign_token = None
        if len(model.sections) == 1:
            section = next(iter(model.sections))
            body = getattr(section, "body", None)
            if body is not None and len(body) == 1:
                t = next(iter(body))
                if t.__class__.__name__ == "TestCase":
                    body = getattr(t, "body", None)
                    if len(body) == 1:
                        line = next(iter(body))
                        if line.__class__.__name__ == "KeywordCall":
                            if not line.keyword:
                                for token in line.tokens:
                                    if token.type == token.ASSIGN:
                                        assign_token = token
                                        break

                        elif line.__class__.__name__ == "EmptyLine":
                            for token in line.tokens:
                                if token.type == token.ASSIGN:
                                    assign_token = token
                                    break

        if assign_token:
            return context.namespace.variables.replace_string(str(token))

        from robot import version

        IS_ROBOT_4_ONWARDS = not version.get_version().startswith("3.")
        if IS_ROBOT_4_ONWARDS:
            if len(test.body) == 1:
                # Unfortunately bodyrunner.BodyRunner.run doesn't return the
                # value, so, we have to do it ourselves.
                from robot.errors import ExecutionPassed
                from robot.errors import ExecutionFailed
                from robot.errors import ExecutionFailures

                errors = []
                passed = None
                step = next(iter(test.body))
                ret = None
                try:
                    ret = step.run(context, True, False)
                except ExecutionPassed as exception:
                    exception.set_earlier_failures(errors)
                    passed = exception
                except ExecutionFailed as exception:
                    errors.extend(exception.get_errors())
                if passed:
                    raise passed
                if errors:
                    raise ExecutionFailures(errors)
                return ret

            from robot.running.bodyrunner import BodyRunner  # noqa

            BodyRunner(context, templated=False).run(test.body)
            return None
        else:
            from robot.running.steprunner import StepRunner  # noqa

            StepRunner(context, False).run_steps(test.keywords.normal)
            return None

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
