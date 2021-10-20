import pytest
from typing import Dict, List
import threading
from robocorp_ls_core.basic import wait_for_condition


class _Setup:
    def __init__(self, rf_interpreter_server_manager, received_messages, uri):
        from robotframework_interactive.server.rf_interpreter_server_manager import (
            RfInterpreterServerManager,
        )

        self.rf_interpreter_server_manager: RfInterpreterServerManager = (
            rf_interpreter_server_manager
        )
        self.received_messages: List[Dict] = received_messages
        self.uri = uri


@pytest.fixture
def setup(tmpdir):
    from robotframework_interactive.server.rf_interpreter_server_manager import (
        RfInterpreterServerManager,
    )
    from robocorp_ls_core import uris

    received_messages = []

    def on_interpreter_message(msg):
        received_messages.append(msg)

    uri = uris.from_fs_path(str(tmpdir.join("my.robot")))
    rf_interpreter_server_manager = RfInterpreterServerManager(
        on_interpreter_message=on_interpreter_message, uri=uri
    )
    yield _Setup(rf_interpreter_server_manager, received_messages, uri)
    rf_interpreter_server_manager.interpreter_stop()


def test_robot_pythonpath(setup: _Setup, tmpdir):
    received_messages = setup.received_messages
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    config = rf_interpreter_server_manager.config

    folder = tmpdir.join("some áéíóú folder")
    folder.mkdir()

    my_module = folder.join("my_module.py")
    my_module.write_text(
        """
def some_method():
    return 'Some Method Executed'
""",
        "utf-8",
    )

    config.update({"robot.pythonpath": [str(folder)]})

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    del received_messages[:]

    result = rf_interpreter_server_manager.interpreter_evaluate(
        """
*** Settings ***
Library    my_module.py
"""
    )
    assert result["success"], f"Found: {result}"
    del received_messages[:]

    result = rf_interpreter_server_manager.interpreter_evaluate(
        """
*** Task ***
Some task
    ${x}=    Some Method
    Log    ${x}     console=True
"""
    )
    assert result["success"], f"Found: {result}"
    assert received_messages == [
        {
            "jsonrpc": "2.0",
            "method": "interpreter/output",
            "params": {"output": "Some Method Executed\n", "category": "stdout"},
        }
    ]


def test_server_basic(setup: _Setup):
    received_messages = setup.received_messages
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert not result["success"], f"Found: {result}"  # i.e.: already initialized

    del received_messages[:]

    result = rf_interpreter_server_manager.interpreter_evaluate(
        """
*** Task ***
Some task
    Log    Something     console=True
"""
    )

    assert received_messages == [
        {
            "jsonrpc": "2.0",
            "method": "interpreter/output",
            "params": {"output": "Something\n", "category": "stdout"},
        }
    ]

    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        """Log    Foo     console=True"""
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "*** Test Case ***\nDefault Task/Test\n",
            "indent": "    ",
            "full_code": "*** Test Case ***\nDefault Task/Test\n    Log    Foo     console=True",
        },
    }

    result = rf_interpreter_server_manager.interpreter_stop()

    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert not result[
        "success"
    ], f"Found: {result}"  # i.e.: already initialized (cannot reinitialize)


def test_server_stdin(setup: _Setup):
    from robocorp_ls_core import uris
    import os

    received_messages = setup.received_messages
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"
    uri = setup.uri
    robot_file = uris.to_fs_path(uri)
    lib_file = os.path.join(os.path.dirname(robot_file), "my_lib.py")
    with open(lib_file, "w", encoding="utf-8") as stream:
        stream.write(
            r"""
def check_input():
    import sys
    sys.__stdout__.write('Enter something\n')
    return input()
"""
        )
    rf_interpreter_server_manager.interpreter_evaluate(
        "*** Settings ***\nLibrary    ./my_lib.py"
    )

    def check_input_in_thread():
        rf_interpreter_server_manager.interpreter_evaluate("Check Input")

    threading.Thread(target=check_input_in_thread).start()

    def wait_for_enter_something_output():
        for msg in received_messages:
            if (
                msg["method"] == "interpreter/output"
                and "Enter something" in msg["params"]["output"]
            ):
                return True
        return False

    wait_for_condition(wait_for_enter_something_output)
    assert rf_interpreter_server_manager._get_api_client().waiting_input
    rf_interpreter_server_manager.interpreter_evaluate("Something\n")


def test_server_full_code_01(setup: _Setup):
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_evaluate(
        """
*** Task ***
Some task
    Log    Something     console=True
"""
    )

    result = rf_interpreter_server_manager.interpreter_evaluate(
        "Log    Else     console=True"
    )

    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "Log    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n",
            "indent": "    ",
            "full_code": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n    Log    Foo     console=True",
        },
    }

    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "Log    Bar\nLog    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n",
            "indent": "    ",
            "full_code": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n    Log    Bar\n    Log    Foo     console=True",
        },
    }


def test_server_full_code_02(setup: _Setup):
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    # Before first evaluation
    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "Log    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "\n*** Test Case ***\nDefault Task/Test\n",
            "indent": "    ",
            "full_code": "\n*** Test Case ***\nDefault Task/Test\n    Log    Foo     console=True",
        },
    }


def test_server_full_code_03(setup: _Setup):
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    # Before first evaluation
    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "\n\nLog    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "\n*** Test Case ***\nDefault Task/Test\n",
            "indent": "    ",
            "full_code": "\n*** Test Case ***\nDefault Task/Test\n    \n    \n    Log    Foo     console=True",
        },
    }


def test_server_full_code_04(setup: _Setup):
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    # This does nothing in practice
    result = rf_interpreter_server_manager.interpreter_evaluate(
        "*** Task ***\nTask name"
    )

    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "\n\nLog    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "\n*** Test Case ***\nDefault Task/Test\n",
            "indent": "    ",
            "full_code": "\n*** Test Case ***\nDefault Task/Test\n    \n    \n    Log    Foo     console=True",
        },
    }


def test_server_full_code_05(setup: _Setup):
    rf_interpreter_server_manager = setup.rf_interpreter_server_manager

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert result["success"], f"Found: {result}"

    # This does nothing in practice
    result = rf_interpreter_server_manager.interpreter_evaluate(
        "*** Task ***\nTask name"
    )

    result = rf_interpreter_server_manager.interpreter_compute_evaluate_text(
        "\n\nLog    Foo     console=True", target_type="completions"
    )
    assert result == {
        "success": True,
        "message": None,
        "result": {
            "prefix": "\n*** Test Case ***\nDefault Task/Test\n",
            "indent": "    ",
            "full_code": "\n*** Test Case ***\nDefault Task/Test\n    \n    \n    Log    Foo     console=True",
        },
    }
