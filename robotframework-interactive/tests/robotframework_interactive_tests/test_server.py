import pytest
from typing import Dict, List


class _Setup:
    def __init__(self, rf_interpreter_server_manager, received_messages, uri):
        from robotframework_interactive.server.rf_interpreter_server_manager import (
            RfInterpreterServerManager,
        )

        self.rf_interpreter_server_manager: RfInterpreterServerManager = rf_interpreter_server_manager
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

    rf_interpreter_server_manager = RfInterpreterServerManager(
        on_interpreter_message=on_interpreter_message
    )
    uri = uris.from_fs_path(str(tmpdir.join("my.robot")))
    yield _Setup(rf_interpreter_server_manager, received_messages, uri)
    rf_interpreter_server_manager.interpreter_stop()


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
            "prefix": "*** Test Case ***\nDefault Task/Test\n    ",
            "full_code": "*** Test Case ***\nDefault Task/Test\n    Log    Foo     console=True",
        },
    }

    result = rf_interpreter_server_manager.interpreter_stop()

    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_start(setup.uri)
    assert not result[
        "success"
    ], f"Found: {result}"  # i.e.: already initialized (cannot reinitialize)


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
            "prefix": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n    ",
            "full_code": "*** Task ***\nSome task\n    Log    Something     console=True\n\n    Log    Else     console=True\n    Log    Foo     console=True",
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
            "prefix": "\n*** Test Case ***\nDefault Task/Test\n    ",
            "full_code": "\n*** Test Case ***\nDefault Task/Test\n    Log    Foo     console=True",
        },
    }
