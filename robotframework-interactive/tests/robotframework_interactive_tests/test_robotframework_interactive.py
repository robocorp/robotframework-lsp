import pytest


@pytest.fixture(scope="function")
def change_test_dir(tmpdir):
    import os

    cwd = os.path.abspath(os.getcwd())
    os.chdir(tmpdir)
    yield
    os.chdir(cwd)


def test_basic(change_test_dir):
    from robotframework_interactive.interpreter import RobotFrameworkInterpreter
    from io import StringIO
    from robot.running.context import EXECUTION_CONTEXTS

    interpreter = RobotFrameworkInterpreter()

    stream_stdout = StringIO()
    stream_stderr = StringIO()

    def on_stdout(msg: str):
        stream_stdout.write(msg)

    def on_stderr(msg: str):
        stream_stderr.write(msg)

    interpreter.on_stdout.register(on_stdout)
    interpreter.on_stderr.register(on_stderr)

    class _info(object):
        on_main_loop_called = False

    def on_main_loop(interpreter: RobotFrameworkInterpreter):
        _info.on_main_loop_called = True
        assert "Default test suite" in stream_stdout.getvalue()
        assert "Output:" not in stream_stdout.getvalue()

        assert (
            "Collections"
            not in EXECUTION_CONTEXTS.current.namespace._kw_store.libraries
        )
        interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")
        assert "Collections" in EXECUTION_CONTEXTS.current.namespace._kw_store.libraries

        # Reimport is ok...
        interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")

        # Error if library does not exist.
        interpreter.evaluate("""*** Settings ***\nLibrary    ErrorNotThere""")
        assert "No module named 'ErrorNotThere'" in stream_stderr.getvalue()

    interpreter.initialize(on_main_loop)

    assert _info.on_main_loop_called
    assert "Output:" in stream_stdout.getvalue()
    # print(stream_stdout.getvalue())


def test_robotframework_api(change_test_dir):
    from robot.api import TestSuite, get_model  # noqa
    import os
    from io import StringIO

    model = get_model(
        """
*** Settings ***
Library    Collections

*** Test Case ***
Some Test
    Log    Something
"""
    )

    test_suite = TestSuite.from_model(model)

    stdout = StringIO()
    test_suite.run(output=os.path.abspath("output.xml"), stdout=stdout)
