def test_server():
    from robotframework_interactive.server.rf_interpreter_server_manager import (
        RfInterpreterServerManager,
    )

    received_messages = []

    def on_interpreter_message(msg):
        received_messages.append(msg)

    rf_interpreter_server_manager = RfInterpreterServerManager(
        on_interpreter_message=on_interpreter_message
    )
    result = rf_interpreter_server_manager.interpreter_start()
    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_start()
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

    result = rf_interpreter_server_manager.interpreter_stop()

    assert result["success"], f"Found: {result}"

    result = rf_interpreter_server_manager.interpreter_start()
    assert not result[
        "success"
    ], f"Found: {result}"  # i.e.: already initialized (cannot reinitialize)
