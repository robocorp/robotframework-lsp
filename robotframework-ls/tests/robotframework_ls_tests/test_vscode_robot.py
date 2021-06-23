import logging
import os
from robocorp_ls_core.protocols import ILanguageServerClient


log = logging.getLogger(__name__)


def check_diagnostics(language_server, data_regression):
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT
    from robotframework_ls_tests.fixtures import sort_diagnostics

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
    diag = message_matcher.msg["params"]["diagnostics"]
    data_regression.check(sort_diagnostics(diag), basename="diagnostics")


def test_diagnostics(language_server, ws_root_path, data_regression):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    import robot

    env = {
        "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(robot.__file__)))
    }
    language_server.settings(
        {"settings": {"robot.python.env": env, "robot.lint.robocop.enabled": True}}
    )
    check_diagnostics(language_server, data_regression)


def test_diagnostics_robocop(language_server, ws_root_path, data_regression):
    from robotframework_ls_tests.fixtures import sort_diagnostics
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

    language_server.initialize(ws_root_path, process_id=os.getpid())

    language_server.settings({"settings": {"robot.lint.robocop.enabled": True}})

    uri = "untitled:Untitled-1"
    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}
    )
    language_server.open_doc(uri, 1)
    assert message_matcher.event.wait(TIMEOUT)

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}
    )
    language_server.change_doc(
        uri,
        2,
        """
*** Test Cases ***
Test
    Fail
    
Test
    Fail
""",
    )
    assert message_matcher.event.wait(TIMEOUT)
    diag = message_matcher.msg["params"]["diagnostics"]
    data_regression.check(sort_diagnostics(diag), basename="test_diagnostics_robocop")


def test_diagnostics_robocop_configuration_file(
    language_server, ws_root_path, data_regression
):
    from robotframework_ls_tests.fixtures import sort_diagnostics
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT
    from robocorp_ls_core import uris

    language_server.initialize(ws_root_path, process_id=os.getpid())
    language_server.settings({"settings": {"robot.lint.robocop.enabled": True}})
    src = os.path.join(ws_root_path, "my", "src")
    os.makedirs(src)
    target_robot = os.path.join(src, "target.robot")
    config_file = os.path.join(ws_root_path, "my", ".robocop")
    with open(config_file, "w") as stream:
        stream.write(
            """
--exclude missing-doc-testcase
--include missing-doc-suite
"""
        )

    uri = uris.from_fs_path(target_robot)
    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}
    )
    language_server.open_doc(
        uri,
        1,
        text="""
*** Test Cases ***
Test
    Fail

""",
    )
    assert message_matcher.event.wait(TIMEOUT)
    diag = message_matcher.msg["params"]["diagnostics"]
    data_regression.check(
        sort_diagnostics(diag), basename="test_diagnostics_robocop_configuration_file"
    )


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


def test_keyword_completions_integrated_pythonpath_resource(
    language_server_tcp, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    case4_path = cases.get_path("case4")

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Settings ***
Resource    case4resource.txt

*** Test Cases ***
Check It
    Yet Another Equ"""
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings({"settings": {"robot": {"pythonpath": [case4_path]}}})

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    data_regression.check(request_completion())

    # Removing should no longer find it.
    language_server_tcp.settings({"settings": {"robot": {"pythonpath": []}}})

    data_regression.check(request_completion(), basename="no_entries")


def test_keyword_completions_integrated_pythonpath_library(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    case1_path = cases.get_path("case1")

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Settings ***
Library    case1_library

*** Test Cases ***
Check It
    Verify Mod"""
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings({"settings": {"robot": {"pythonpath": [case1_path]}}})

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    data_regression.check(request_completion())

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings({"settings": {"robot": {"pythonpath": []}}})

    data_regression.check(request_completion())


def test_completions_after_library(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    case1_path = cases.get_path("case1")

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Settings ***
Library    """
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings({"settings": {"robot": {"pythonpath": [case1_path]}}})

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    assert not request_completion()["result"]


def test_keyword_completions_prefer_local_library_import(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document
    from robocorp_ls_core import uris

    try:
        os.makedirs(ws_root_path)
    except:
        pass

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    case1_robot_path = cases.get_path("case1/case1.robot")
    contents = """
*** Settings ***
Library           case1_library

*** Test Cases ***
User can call library
    verify model   1
    verify_another_mod"""

    uri = uris.from_fs_path(case1_robot_path)
    language_server.open_doc(uri, 1, text=contents)

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    data_regression.check(request_completion())


def test_variables_completions_integrated(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document

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

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings({"settings": {"robot": {"variables": {"myvar1": 10}}}})

    completions = language_server.get_completions(uri, line, col)
    labels = [x["label"] for x in completions["result"]]
    assert "${myvar1}" in labels


def test_variables_resolved_on_completion_integrated(
    language_server_tcp: ILanguageServerClient, workspace_dir, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(workspace_dir, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """*** Settings ***
Library           ${ROOT}/directory/my_library.py


*** Keywords ***
Some Keyword
    In Lib"""
    language_server.change_doc(uri, 2, contents)

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings(
        {
            "settings": {
                "robot": {"variables": {"ROOT": cases.get_path("case_same_basename")}}
            }
        }
    )

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()
    completions = language_server.get_completions(uri, line, col)
    data_regression.check(completions)


def test_env_variables_resolved_on_completion_integrated(
    language_server_tcp: ILanguageServerClient, workspace_dir, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(workspace_dir, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """*** Settings ***
Library           %{ROOT}/directory/my_library.py


*** Keywords ***
Some Keyword
    In Lib"""
    language_server.change_doc(uri, 2, contents)

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings(
        {
            "settings": {
                "robot": {
                    "python": {"env": {"ROOT": cases.get_path("case_same_basename")}}
                }
            }
        }
    )

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()
    completions = language_server.get_completions(uri, line, col)
    data_regression.check(completions)

    contents = """*** Settings ***
Library           %{ROOT}/directory/my_library.py


*** Keywords ***
Some Keyword
    In Lib 2"""
    language_server.change_doc(uri, 2, contents)
    definitions = language_server.find_definitions(uri, line, col)
    found = definitions["result"]
    assert len(found) == 1
    assert found[0]["uri"].endswith("my_library.py")


def test_snippets_completions_integrated(
    language_server_tcp, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Test Cases ***
List Variable
    for in"""
    language_server.change_doc(uri, 2, contents)

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()
    completions = language_server.get_completions(uri, line, col)
    del completions["id"]
    data_regression.check(completions, "snippet_completions")


def test_restart_when_api_dies(language_server_tcp, ws_root_path, data_regression):
    from robocorp_ls_core.basic import kill_process_and_subprocesses
    from robocorp_ls_core import basic
    from robotframework_ls.server_manager import _ServerApi
    import time

    # Check just with language_server_tcp as it's easier to kill the subprocess.

    server_apis = set()
    server_processes = set()

    def on_get_robotframework_api_client(server_api):
        if (
            server_api.robot_framework_language_server
            is language_server_tcp.language_server_instance
        ):
            server_apis.add(server_api)
            server_processes.add(server_api._server_process.pid)

    with basic.after(
        _ServerApi, "get_robotframework_api_client", on_get_robotframework_api_client
    ):
        language_server_tcp.initialize(ws_root_path, process_id=os.getpid())
        import robot

        env = {
            "PYTHONPATH": os.path.dirname(
                os.path.dirname(os.path.abspath(robot.__file__))
            )
        }
        language_server_tcp.settings(
            {"settings": {"robot.python.env": env, "robot.lint.robocop.enabled": True}}
        )

        processes_per_api = 3

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == processes_per_api
        assert len(server_processes) == processes_per_api

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_apis) == processes_per_api
        assert len(server_processes) == processes_per_api

        log.info("Killing server api process.")
        for pid in server_processes:
            kill_process_and_subprocesses(pid)

        # Just make sure the connection is properly dropped before re-requesting.
        time.sleep(0.2)

        check_diagnostics(language_server_tcp, data_regression)
        assert len(server_processes) == processes_per_api * 2
        assert len(server_apis) == processes_per_api


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
    from robocorp_ls_core.subprocess_wrapper import subprocess
    import sys
    from robocorp_ls_core.basic import is_process_alive
    from robocorp_ls_core.basic import kill_process_and_subprocesses
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

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


def test_find_definition_integrated_library(
    language_server: ILanguageServerClient, cases, workspace_dir
):
    from robocorp_ls_core import uris

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


def test_find_definition_keywords(
    language_server: ILanguageServerClient, cases, workspace_dir
):
    from robocorp_ls_core import uris

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


def test_signature_help_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Cases ***
Log It
    Log    """
    doc = Document("", txt)
    language_server.open_doc(uri, 1, txt)
    line, col = doc.get_last_line_col()

    ret = language_server.request_signature_help(uri, line, col)
    result = ret["result"]
    signatures = result["signatures"]

    # Don't check the signature documentation in the data regression so that the
    # test doesn't become brittle.
    docs = signatures[0].pop("documentation")
    assert "Log" in docs

    data_regression.check(result)


def test_hover_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document
    from robocorp_ls_core.lsp import HoverTypedDict

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Cases ***
Log It
    Log    """
    doc = Document("", txt)
    language_server.open_doc(uri, 1, txt)
    line, col = doc.get_last_line_col()

    ret = language_server.request_hover(uri, line, col)
    result: HoverTypedDict = ret["result"]

    contents = result["contents"]
    assert "Log" in contents["value"]
    assert contents["kind"] == "markdown"


def test_workspace_symbols_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())

    ret = language_server.request_workspace_symbols()
    result = ret["result"]
    assert len(result) > 0


def test_folding_range_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Cases ***
Log It
    Log    

Log It2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_folding_range(uri)
    result = ret["result"]
    data_regression.check(result)


def test_code_lens_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Case ***
Log It
    Log    

*** Task ***
Log It2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_code_lens(uri)
    found = ret["result"]
    data_regression.check(found)


def test_code_lens_integrated_suites(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Task ***
Log It
    Log    

Log It2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_code_lens(uri)
    found = ret["result"]
    data_regression.check(found)


def test_list_tests_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Case ***
Log It
    Log    

*** Task ***
Log It2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.execute_command("robot.listTests", [{"uri": uri}])
    found = ret["result"]
    data_regression.check(found)


def test_document_symbol_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Task ***
Log It
    Log    

Log It2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_document_symbol(uri)
    found = ret["result"]
    data_regression.check(found)


def test_shadowing_libraries(language_server_io: ILanguageServerClient, workspace_dir):
    from robocorp_ls_core import uris
    from pathlib import Path
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

    language_server = language_server_io

    os.makedirs(workspace_dir, exist_ok=True)
    builtin_lib = Path(workspace_dir) / "builtin.py"
    case1_lib = Path(workspace_dir) / "case1.robot"
    case2_lib = Path(workspace_dir) / "case2.robot"

    builtin_lib.write_text(
        """
def something():
    pass
"""
    )

    case1_lib.write_text(
        """
*** Settings ***
Library           builtin

*** Test Cases ***
User can call builtin
    Something
"""
    )

    case2_lib.write_text(
        """
*** Test Cases ***
User can call builtin 2
    Log  Task executed
"""
    )

    language_server.initialize(workspace_dir, process_id=os.getpid())

    uri1 = uris.from_fs_path(str(case1_lib))
    uri2 = uris.from_fs_path(str(case2_lib))

    for _i in range(2):
        message_matcher = language_server.obtain_pattern_message_matcher(
            {"method": "textDocument/publishDiagnostics"}
        )

        language_server.open_doc(uri1, 1, text=None)
        assert message_matcher.event.wait(TIMEOUT)
        assert message_matcher.msg["params"]["uri"] == uri1
        assert message_matcher.msg["params"]["diagnostics"] == []

        message_matcher = language_server.obtain_pattern_message_matcher(
            {"method": "textDocument/publishDiagnostics"}
        )

        language_server.open_doc(uri2, 1, text=None)
        assert message_matcher.event.wait(TIMEOUT)
        assert message_matcher.msg["params"]["uri"] == uri2
        assert message_matcher.msg["params"]["diagnostics"] == []

        language_server.close_doc(uri2)
        language_server.close_doc(uri1)


def test_rf_interactive_integrated(
    language_server_io: ILanguageServerClient, ws_root_path
):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_START
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_STOP
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())

    ret1 = language_server.execute_command(ROBOT_INTERNAL_RFINTERACTIVE_START, [])
    assert ret1["result"] == {
        "success": True,
        "message": None,
        "result": {"interpreter_id": 0},
    }

    ret2 = language_server.execute_command(ROBOT_INTERNAL_RFINTERACTIVE_START, [])
    assert ret2["result"] == {
        "success": True,
        "message": None,
        "result": {"interpreter_id": 1},
    }

    stop1 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 0}]
    )
    assert stop1["result"] == {"success": True, "message": None, "result": None}

    stop_inexistant = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 22}]
    )
    assert stop_inexistant["result"] == {
        "success": False,
        "message": "Did not find interpreter with id: 22",
        "result": None,
    }

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "interpreter/output"}
    )
    eval2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        [
            {
                "interpreter_id": 1,
                "code": """
*** Task ***
Some task
    Log    Something     console=True
""",
            }
        ],
    )
    assert eval2["result"] == {"success": True, "message": None, "result": None}
    assert message_matcher.event.wait(10)
    assert message_matcher.msg == {
        "jsonrpc": "2.0",
        "method": "interpreter/output",
        "params": {"output": "Something\n", "category": "stdout", "interpreter_id": 1},
    }

    semantic_tokens = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS,
        [{"interpreter_id": 1, "code": "Log    Something     console=True"}],
    )

    data = semantic_tokens["result"]["data"]
    assert data == [
        0,
        0,
        3,
        7,
        0,
        0,
        7,
        9,
        12,
        0,
        0,
        14,
        7,
        11,
        0,
        0,
        7,
        1,
        6,
        0,
        0,
        1,
        4,
        12,
        0,
    ]

    stop2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 1}]
    )
    assert stop2["result"] == {"success": True, "message": None, "result": None}
