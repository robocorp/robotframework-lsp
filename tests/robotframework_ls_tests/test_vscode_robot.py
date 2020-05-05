import logging
import os

from robotframework_ls_tests.fixtures import TIMEOUT


log = logging.getLogger(__name__)


def check_diagnostics(language_server, data_regression):
    uri = "untitled:Untitled-1"
    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}
    )
    language_server.open_doc(uri, 1)
    assert message_matcher.event.wait(TIMEOUT)

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}
    )
    language_server.change_doc(uri, 2, "*** Invalid Invalid ***")
    assert message_matcher.event.wait(TIMEOUT)
    diag = message_matcher.msg

    data_regression.check(diag, basename="diagnostics")


def test_diagnostics(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    import robot

    env = {
        "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(robot.__file__)))
    }
    language_server.settings({"settings": {"robot": {"python": {"env": env}}}})
    check_diagnostics(language_server, data_regression)


def test_section_completions_integrated(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    language_server.change_doc(uri, 2, "*settin")

    def check(expected):
        completions = language_server.get_completions(uri, 0, 7)
        del completions["id"]
        data_regression.check(completions, expected)

    check("completion_settings_plural")

    language_server.settings(
        {
            "settings": {
                "robot": {"completions": {"section_headers": {"form": "singular"}}}
            }
        }
    )
    check("completion_settings_singular")

    language_server.settings(
        {"settings": {"robot": {"completions": {"section_headers": {"form": "both"}}}}}
    )
    check("completion_settings_both")

    language_server.settings(
        {
            "settings": {
                "robot": {"completions": {"section_headers": {"form": "plural"}}}
            }
        }
    )
    check("completion_settings_plural")


def test_variables_completions_integrated(
    language_server_tcp, ws_root_path, data_regression
):
    from robotframework_ls.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Variables ***
${NAME}         Robot Framework
${VERSION}      2.0
${ROBOT}        ${NAME} ${VERSION}

*** Test Cases ***
List Variable
    Log    ${NAME}
    Should Contain    ${"""
    language_server.change_doc(uri, 2, contents)

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()
    completions = language_server.get_completions(uri, line, col)
    del completions["id"]
    data_regression.check(completions, "variable_completions")


def test_restart_when_api_dies(language_server_tcp, ws_root_path, data_regression):
    from robotframework_ls import _utils
    from robotframework_ls._utils import kill_process_and_subprocesses

    # Check just with language_server_tcp as it's easier to kill the subprocess.
    from robotframework_ls.robotframework_ls_impl import _ServerApi

    server_apis = set()
    server_processes = set()

    def on_get_server_api(server_api):
        if (
            server_api.robot_framework_language_server
            is language_server_tcp.language_server_instance
        ):
            # do something else
            server_apis.add(server_api)
            server_processes.add(server_api._server_process.pid)

    with _utils.after(_ServerApi, "_get_server_api", on_get_server_api):
        language_server_tcp.initialize(ws_root_path, process_id=os.getpid())
        import robot

        env = {
            "PYTHONPATH": os.path.dirname(
                os.path.dirname(os.path.abspath(robot.__file__))
            )
        }
        language_server_tcp.settings({"settings": {"robot": {"python": {"env": env}}}})

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == 1
        assert len(server_processes) == 1

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == 1
        assert len(server_processes) == 1

        log.debug("Killing server api process.")
        for pid in server_processes:
            kill_process_and_subprocesses(pid)

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_processes) == 2
        assert len(server_apis) == 1


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
    language_server_process, language_server_io, ws_root_path
):
    """
    :note: Only check with the language_server_io (because that's in another process).
    """
    import subprocess
    import sys
    from robotframework_ls_tests.fixtures import wait_for_condition
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


def test_code_format_integrated(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    language_server.change_doc(uri, 2, "***settings***\nDocumentation  Some doc")
    ret = language_server.request_source_format(uri)
    data_regression.check(ret, basename="test_code_format_integrated_text_edits")

    language_server.change_doc(uri, 3, "[Documentation]\n")
    ret = language_server.request_source_format(uri)
    assert ret["result"] == []


def test_find_definition_integrated_library(language_server, cases, tmpdir):
    from robotframework_ls import uris

    workspace_dir = str(tmpdir.join("workspace"))
    cases.copy_to("case1", workspace_dir)

    language_server.initialize(workspace_dir, process_id=os.getpid())
    case1_robot = os.path.join(workspace_dir, "case1.robot")
    assert os.path.exists(case1_robot)
    uri = uris.from_fs_path(case1_robot)

    language_server.open_doc(uri, 1, text=None)
    ret = language_server.find_definitions(uri, 5, 6)
    result = ret["result"]
    assert len(result) == 1
    check = next(iter(result))
    assert check["uri"].endswith("case1_library.py")
    assert check["range"] == {
        "start": {"line": 7, "character": 0},
        "end": {"line": 7, "character": 0},
    }


def test_find_definition_keywords(language_server, cases, tmpdir):
    from robotframework_ls import uris

    workspace_dir = str(tmpdir.join("workspace"))
    cases.copy_to("case2", workspace_dir)

    language_server.initialize(workspace_dir, process_id=os.getpid())
    case2_robot = os.path.join(workspace_dir, "case2.robot")
    assert os.path.exists(case2_robot)
    uri = uris.from_fs_path(case2_robot)

    language_server.open_doc(uri, 1, text=None)
    ret = language_server.find_definitions(uri, 7, 6)
    result = ret["result"]
    assert len(result) == 1
    check = next(iter(result))
    assert check["uri"].endswith("case2.robot")
    assert check["range"] == {
        "start": {"line": 1, "character": 0},
        "end": {"line": 4, "character": 5},
    }
