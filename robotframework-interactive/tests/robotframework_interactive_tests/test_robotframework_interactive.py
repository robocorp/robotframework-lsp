import pytest
from robotframework_interactive.interpreter import RobotFrameworkInterpreter
import threading
from io import StringIO


@pytest.fixture(scope="function")
def change_test_dir(tmpdir):
    import os

    cwd = os.path.abspath(os.getcwd())
    os.chdir(tmpdir)
    yield
    os.chdir(cwd)


from dataclasses import dataclass


@dataclass
class _InterpreterInfo:
    interpreter: RobotFrameworkInterpreter
    stream_stdout: StringIO
    stream_stderr: StringIO


@pytest.fixture
def interpreter(change_test_dir):
    """
    Note: we rely on callbacks as we can't yield from the main loop (because the
    APIs on robot framework are blocking), so, we start up in a thread and then
    when the interpreter is in the main loop we return from that paused state
    and at tear-down we stop that thread.
    """
    interpreter = RobotFrameworkInterpreter()

    stream_stdout = StringIO()
    stream_stderr = StringIO()

    def on_stdout(msg: str):
        stream_stdout.write(msg)

    def on_stderr(msg: str):
        stream_stderr.write(msg)

    interpreter.on_stdout.register(on_stdout)
    interpreter.on_stderr.register(on_stderr)

    started_main_loop_event = threading.Event()
    finish_main_loop_event = threading.Event()

    def run_on_thread():
        def on_main_loop(interpreter: RobotFrameworkInterpreter):
            started_main_loop_event.set()
            finish_main_loop_event.wait()

        interpreter.initialize(on_main_loop)
        assert "Output:" in stream_stdout.getvalue()

    t = threading.Thread(target=run_on_thread)
    t.start()
    assert started_main_loop_event.wait(5)
    yield _InterpreterInfo(interpreter, stream_stdout, stream_stderr)
    finish_main_loop_event.set()


def test_basic(interpreter):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    EXECUTION_CONTEXTS = facade.EXECUTION_CONTEXTS

    assert "Default test suite" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    assert "Collections" not in EXECUTION_CONTEXTS.current.namespace._kw_store.libraries
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")
    assert "Collections" in EXECUTION_CONTEXTS.current.namespace._kw_store.libraries

    # Reimport is ok...
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")

    # Error if library does not exist.
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    ErrorNotThere""")
    assert "No module named 'ErrorNotThere'" in interpreter.stream_stderr.getvalue()


def test_robotframework_api(change_test_dir):
    from robot.api import TestSuite, get_model  # noqa
    import os

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
