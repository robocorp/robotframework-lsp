import logging
from robocode_ls_core.protocols import ILanguageServerClient
import os.path
import sys

log = logging.getLogger(__name__)


def test_missing_message(language_server: ILanguageServerClient, ws_root_path):
    language_server.initialize(ws_root_path)

    # Just ignore this one (it's not a request because it has no id).
    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "invalidMessageSent",
            "params": {"textDocument": {"uri": "untitled:Untitled-1", "version": 2}},
        }
    )

    # Make sure that we have a response if it's a request (i.e.: it has an id).
    msg = language_server.request(
        {
            "jsonrpc": "2.0",
            "id": "22",
            "method": "invalidMessageSent",
            "params": {"textDocument": {"uri": "untitled:Untitled-1", "version": 2}},
        }
    )

    assert msg["error"]["code"] == -32601


def test_exit_with_parent_process_died(
    language_server_process: ILanguageServerClient, language_server_io, ws_root_path
):
    """
    :note: Only check with the language_server_io (because that's in another process).
    """
    from robocode_ls_core.subprocess_wrapper import subprocess
    from robocode_ls_core.basic import is_process_alive
    from robocode_ls_core.basic import kill_process_and_subprocesses
    from robocode_ls_core.unittest_tools.fixtures import wait_for_test_condition

    language_server = language_server_io
    dummy_process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(10000)"]
    )

    language_server.initialize(ws_root_path, process_id=dummy_process.pid)

    assert is_process_alive(dummy_process.pid)
    assert is_process_alive(language_server_process.pid)

    kill_process_and_subprocesses(dummy_process.pid)

    wait_for_test_condition(lambda: not is_process_alive(dummy_process.pid))
    wait_for_test_condition(lambda: not is_process_alive(language_server_process.pid))
    language_server_io.require_exit_messages = False


def test_list_rcc_activity_templates(
    language_server_tcp: ILanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    tmpdir,
):
    from robocode_vscode import commands
    import json

    assert os.path.exists(rcc_location)
    language_server = language_server_tcp
    language_server.initialize(ws_root_path)
    language_server.settings(
        {"settings": {"robocode": {"rcc": {"location": rcc_location}}}}
    )

    result = language_server.execute_command(
        commands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL, []
    )["result"]
    assert isinstance(result, list)
    assert result == ["basic", "minimal"]

    target = str(tmpdir.join("dest"))
    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    assert result == {"result": "ok"}

    # Error
    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    sys.stderr.write(json.dumps((result)))
    assert result["result"] == "error"
    assert "Error creating activity" in result["message"]
