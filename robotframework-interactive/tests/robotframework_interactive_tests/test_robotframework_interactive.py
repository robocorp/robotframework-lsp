from dataclasses import dataclass
from io import StringIO
import os
import sys
import threading

import pytest

from robotframework_interactive.interpreter import RobotFrameworkInterpreter


USE_TIMEOUTS = True
if "GITHUB_WORKFLOW" not in os.environ:
    if "pydevd" in sys.modules:
        USE_TIMEOUTS = False


@pytest.fixture(scope="function")
def change_test_dir(tmpdir):
    cwd = os.path.abspath(os.getcwd())
    os.chdir(tmpdir)
    yield
    os.chdir(cwd)


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
    finished_main_loop_event = threading.Event()

    def run_on_thread():
        def on_main_loop(interpreter: RobotFrameworkInterpreter):
            started_main_loop_event.set()
            finish_main_loop_event.wait()
            finished_main_loop_event.set()

        interpreter.initialize(on_main_loop)
        assert "Output:" in stream_stdout.getvalue()

    t = threading.Thread(target=run_on_thread)
    t.start()
    assert started_main_loop_event.wait(5 if USE_TIMEOUTS else None)

    # Ok, at this point it's initialized!
    yield _InterpreterInfo(interpreter, stream_stdout, stream_stderr)

    finish_main_loop_event.set()
    finished_main_loop_event.wait(5 if USE_TIMEOUTS else None)
    # print(stream_stdout.getvalue())
    # print(stream_stderr.getvalue())


def test_basic(interpreter):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    assert "Default test suite" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    assert "Collections" not in facade.get_libraries_imported_in_namespace()
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")
    assert "Collections" in facade.get_libraries_imported_in_namespace()

    # Reimport is ok...
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")

    # Error if library does not exist.
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    ErrorNotThere""")
    assert "No module named 'ErrorNotThere'" in interpreter.stream_stderr.getvalue()


def test_reuse_block_on_line(interpreter):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    assert "Collections" not in facade.get_libraries_imported_in_namespace()
    interpreter.interpreter.evaluate("*** Settings ***")
    assert "Collections" not in facade.get_libraries_imported_in_namespace()
    interpreter.interpreter.evaluate("Library    Collections")
    assert "Collections" in facade.get_libraries_imported_in_namespace()

    interpreter.interpreter.evaluate("*** Task ***")
    # Ok, note that this is different: we always have a task running, so, what
    # we want to do now is directly evaluate instead of considering it the task name.
    interpreter.interpreter.evaluate("Log    Something    console=True")

    assert "Something" in interpreter.stream_stdout.getvalue()
    assert not interpreter.stream_stderr.getvalue()


def test_robotframework_api(change_test_dir):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    get_model = facade.get_model
    TestSuite = facade.TestSuite

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
