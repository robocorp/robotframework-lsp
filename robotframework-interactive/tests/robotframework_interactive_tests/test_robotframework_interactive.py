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
def interpreter(change_test_dir, request):
    """
    Note: we rely on callbacks as we can't yield from the main loop (because the
    APIs on robot framework are blocking), so, we start up in a thread and then
    when the interpreter is in the main loop we return from that paused state
    and at tear-down we stop that thread.
    """
    from robotframework_interactive.server.rf_interpreter_ls_config import (
        RfInterpreterRobotConfig,
    )

    interpreter = RobotFrameworkInterpreter(RfInterpreterRobotConfig())

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

    if request.node.rep_call.failed:
        # Note info made available on conftest.pytest_runtest_makereport.
        print("executing test failed", request.node.nodeid)
        print("============ Interpreter stdout ============")
        print(stream_stdout.getvalue())
        print("============ Interpreter stderr ============")
        print(stream_stderr.getvalue())
        print("============================================")


def test_library_import(interpreter: _InterpreterInfo):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    assert "Robot Interactive Console" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    assert "Collections" not in facade.get_libraries_imported_in_namespace()
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")
    assert "Collections" in facade.get_libraries_imported_in_namespace()

    # Reimport is ok...
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    Collections""")

    # Error if library does not exist.
    interpreter.interpreter.evaluate("""*** Settings ***\nLibrary    ErrorNotThere""")
    assert "No module named 'ErrorNotThere'" in interpreter.stream_stderr.getvalue()


def test_resource_import(interpreter: _InterpreterInfo, tmpdir):
    tmpdir.join("my_robot.robot").write_text(
        """
*** Keyword ***
My Keyword
    Log    MyKeywordCalled    console=True
""",
        encoding="utf-8",
    )
    interpreter.interpreter.evaluate("*** Settings ***\nResource    ./my_robot.robot")
    interpreter.interpreter.evaluate("*** Test Case ***")
    interpreter.interpreter.evaluate("My Keyword")
    assert "MyKeywordCalled" in interpreter.stream_stdout.getvalue()


def test_variables_import(interpreter: _InterpreterInfo, tmpdir):
    tmpdir.join("my_vars.py").write_text(
        """
MY_NAME = "MyNameToPrint"
""",
        encoding="utf-8",
    )
    interpreter.interpreter.evaluate("*** Settings ***\nVariables    ./my_vars.py")
    interpreter.interpreter.evaluate("*** Test Case ***")
    interpreter.interpreter.evaluate("Log    ${MY_NAME}    console=True")
    assert "MyNameToPrint" in interpreter.stream_stdout.getvalue()


def test_variables_section(interpreter: _InterpreterInfo, tmpdir):
    interpreter.interpreter.evaluate(
        """
*** Variables ***
${NAME}         MyNameToPrint
${NAME2}    2ndName
"""
    )

    interpreter.interpreter.evaluate("*** Test Case ***")
    interpreter.interpreter.evaluate("Log    ${NAME} ${NAME2}    console=True")
    assert "MyNameToPrint" in interpreter.stream_stdout.getvalue()
    assert "2ndName" in interpreter.stream_stdout.getvalue()


def test_keyword_section(interpreter: _InterpreterInfo):
    interpreter.interpreter.evaluate(
        """
*** Keywords ***
MyKeyword
    Log    RunningMyKeyword    console=True
"""
    )

    interpreter.interpreter.evaluate("*** Test Case ***")
    interpreter.interpreter.evaluate("MyKeyword")
    assert "RunningMyKeyword" in interpreter.stream_stdout.getvalue()


def test_reuse_block_on_line(interpreter: _InterpreterInfo):
    from robotframework_interactive.robotfacade import RobotFrameworkFacade

    facade = RobotFrameworkFacade()
    assert "Collections" not in facade.get_libraries_imported_in_namespace()
    interpreter.interpreter.evaluate("*** Settings ***\nLibrary    Collections")
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


def test_output_and_errors(interpreter: _InterpreterInfo):
    assert "Robot Interactive Console" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    def on_exception_handled(e):
        if "ignore this error" in str(e):
            return True
        return None

    interpreter.interpreter.on_exception_handled.register(on_exception_handled)
    interpreter.interpreter.evaluate("error here")
    assert (
        interpreter.stream_stderr.getvalue().count("robot.errors.ExecutionFailures")
        == 1
    )
    interpreter.interpreter.evaluate("error here")
    assert (
        interpreter.stream_stderr.getvalue().count("robot.errors.ExecutionFailures")
        == 2
    )

    # Ignored in on_exception_handled
    interpreter.interpreter.evaluate("ignore this error")
    assert (
        interpreter.stream_stderr.getvalue().count("robot.errors.ExecutionFailures")
        == 2
    )


def test_new_lines_and_output_1(interpreter: _InterpreterInfo):
    assert "Robot Interactive Console" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    interpreter.interpreter.evaluate(
        "*** Task ***\r"
        "    ${a}=    Set Variable    somevariabletolog\r"
        "    Log to console    ${a}"
    )
    assert interpreter.stream_stdout.getvalue().count("somevariabletolog") == 1


def test_new_lines_and_output_2(interpreter: _InterpreterInfo):
    assert "Robot Interactive Console" in interpreter.stream_stdout.getvalue()
    assert "Output:" not in interpreter.stream_stdout.getvalue()

    interpreter.interpreter.evaluate(
        "${a}=    Set Variable    somevariabletolog\r" "Log to console    ${a}"
    )
    assert interpreter.stream_stdout.getvalue().count("somevariabletolog") == 1


def test_full_doc_basic(interpreter: _InterpreterInfo):
    evaluate = interpreter.interpreter.evaluate
    contents = (
        ("*** Settings ***\nLibrary    Collections\nLibrary    Process\n"),
        "*** Task ***",
        "Log    Something    console=True",
        "Log    Else    console=True",
    )
    for c in contents:
        evaluate(c)

    full_doc = interpreter.interpreter.full_doc
    assert (
        full_doc == "*** Settings ***\n"
        "Library    Collections\n"
        "Library    Process\n"
        "*** Test Case ***\n"
        "Default Task/Test\n"
        "    Log    Something    console=True\n"
        "    Log    Else    console=True"
    )


def test_full_doc_multiple(interpreter: _InterpreterInfo):
    evaluate = interpreter.interpreter.evaluate
    contents = [
        "*** Settings ***\nLibrary    Collections\nLibrary    Process",
        (
            "*** Task ***\n"
            "Task Name\n"
            "    Log    Something    console=True\n"
            "    Log    Else    console=True"
        ),
        "Log    Foo    console=True",
        (
            "*** Task ***\n"
            "Any task name ignored here\n"
            "    Log    Else    console=True"
        ),
    ]

    for c in contents:
        evaluate(c)

    full_doc = interpreter.interpreter.full_doc
    assert (
        full_doc == "*** Settings ***\n"
        "Library    Collections\n"
        "Library    Process\n"
        "*** Task ***\n"
        "Task Name\n"
        "    Log    Something    console=True\n"
        "    Log    Else    console=True\n"
        "    Log    Foo    console=True\n"
        "    Log    Else    console=True"
    )


def test_redefine_keyword(interpreter: _InterpreterInfo):
    evaluate = interpreter.interpreter.evaluate
    contents = [
        ("*** Keyword ***\n" "My Keyword\n" "    Log  XXXX  console=True\n"),
        "MyKeyword",
        ("*** Keyword ***\n" "My Keyword\n" "    Log  YYYY  console=True\n"),
        "MyKeyword",
    ]

    for c in contents:
        evaluate(c)

    assert not interpreter.stream_stderr.getvalue()
    assert interpreter.stream_stdout.getvalue().count("XXXX") == 1
    assert interpreter.stream_stdout.getvalue().count("YYYY") == 1
    full_doc = interpreter.interpreter.full_doc
    assert full_doc == (
        "*** Keyword ***\n"
        "My Keyword\n"
        "    Log  XXXX  console=True\n"
        "\n"
        "My Keyword\n"
        "    Log  YYYY  console=True\n"
        "*** Test Case ***\n"
        "Default Task/Test\n"
        "    MyKeyword\n"
        "    MyKeyword"
    )


def test_arguments():
    from robotframework_interactive import robotfacade

    facade = robotfacade.RobotFrameworkFacade()

    opts = facade.parse_arguments_options(["--output", "foo"])
    assert opts == {"output": "foo"}

    with pytest.raises(Exception):
        opts = facade.parse_arguments_options(["--invalid-arg", "foo"])
