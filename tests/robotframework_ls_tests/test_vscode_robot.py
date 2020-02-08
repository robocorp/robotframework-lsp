import os


def check_diagnostics(language_server, data_regression):
    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "untitled:Untitled-1",
                    "languageId": "robotframework",
                    "version": 1,
                    "text": "",
                }
            },
        }
    )

    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {"uri": "untitled:Untitled-1", "version": 2},
                "contentChanges": [
                    {
                        "range": {
                            "start": {"line": 0, "character": 0},
                            "end": {"line": 0, "character": 0},
                        },
                        "rangeLength": 0,
                        "text": "*** Invalid Invalid ***",
                    }
                ],
            },
        }
    )

    diag = language_server.wait_for_message(
        {"method": "textDocument/publishDiagnostics"}
    )

    data_regression.check(diag, basename="diagnostics")


def test_diagnostics(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    check_diagnostics(language_server, data_regression)


def test_restart_when_api_dies(language_server_tcp, ws_root_path, data_regression):
    from robotframework_ls import _utils
    from robotframework_ls._utils import kill_process_and_subprocesses

    # Check just with language_server_tcp as it's easier to kill the subprocess.
    from robotframework_ls.robotframework_ls_impl import _ServerApi

    server_apis = set()
    server_processes = set()

    def on_get_server_api(server_api):
        # do something else
        server_apis.add(server_api)
        server_processes.add(server_api._server_process.pid)

    with _utils.after(_ServerApi, "_get_server_api", on_get_server_api):
        language_server_tcp.initialize(ws_root_path, process_id=os.getpid())

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == 1
        assert len(server_processes) == 1

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == 1
        assert len(server_processes) == 1

        for pid in server_processes:
            kill_process_and_subprocesses(pid)

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == 1
        assert len(server_processes) == 2


def test_missing_message(language_server, ws_root_path):
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
    language_server.write(
        {
            "jsonrpc": "2.0",
            "id": "22",
            "method": "invalidMessageSent",
            "params": {"textDocument": {"uri": "untitled:Untitled-1", "version": 2}},
        }
    )

    msg = language_server.wait_for_message({"id": "22"})
    assert msg["error"]["code"] == -32601


def test_exit_with_parent_process_died(
    language_server_process, language_server_io, ws_root_path
):
    """
    :note: Only check with the language_server_io (because that's in another process).
    """
    import subprocess
    import sys
    from robotframework_ls_tests.conftest import wait_for_condition
    from robotframework_ls._utils import is_process_alive
    from robotframework_ls._utils import kill_process_and_subprocesses

    language_server = language_server_io
    dummy_process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(10000)"]
    )

    language_server.initialize(ws_root_path, process_id=dummy_process.pid)

    assert is_process_alive(dummy_process.pid)
    assert is_process_alive(language_server_process.pid)

    kill_process_and_subprocesses(dummy_process.pid)

    wait_for_condition(lambda: not is_process_alive(dummy_process.pid))
    wait_for_condition(lambda: not is_process_alive(language_server_process.pid))
    language_server_io.require_exit_messages = False
