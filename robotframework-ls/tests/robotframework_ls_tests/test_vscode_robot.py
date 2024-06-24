import logging
import os
from pathlib import Path
import threading

import pytest

from robocorp_ls_core.protocols import ILanguageServerClient, ActionResultDict
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_STOP
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY,
    OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY,
)
from robocorp_ls_core.lsp import MarkupKind, WorkspaceEditTypedDict, TextEditTypedDict
import typing
from functools import partial
import itertools
import sys
from robocorp_ls_core.code_units import convert_python_col_to_utf16_code_unit
from typing import List
from robotframework_ls.impl.robot_version import get_robot_major_minor_version


log = logging.getLogger(__name__)


def check_diagnostics(language_server, data_regression):
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT
    from robotframework_ls_tests.fixtures import sort_diagnostics

    uri = "untitled:Untitled-1.resource"
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
    major, minor = get_robot_major_minor_version()
    if (major, minor) >= (6, 1):
        basename = "diagnostics.post.61"
    else:
        basename = "diagnostics"
    data_regression.check(sort_diagnostics(diag), basename=basename)


def check_find_definition_data_regression(data_regression, check, basename=None):
    check["targetUri"] = os.path.basename(check["targetUri"])
    data_regression.check(check, basename=basename)


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


def test_diagnostics_unicode(language_server_tcp, ws_root_path, data_regression):
    language_server = language_server_tcp
    from robotframework_ls_tests.fixtures import sort_diagnostics
    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

    language_server.initialize(ws_root_path, process_id=os.getpid())

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
        """*** Test Cases ***
Unicode
    Log    kangaroo=🦘🦘    level=INFO    er🦘or
""",
    )
    assert message_matcher.event.wait(TIMEOUT)
    diag = message_matcher.msg["params"]["diagnostics"]
    data_regression.check(sort_diagnostics(diag))


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
--exclude missing-doc-test-case
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


def test_diagnostics_workspace(language_server_io, workspace):
    from robotframework_ls.commands import ROBOT_LINT_WORKSPACE, ROBOT_LINT_EXPLORER
    from robocorp_ls_core.basic import wait_for_expected_func_return

    language_server = language_server_io
    workspace.set_root("case_workspace_lint")
    language_server.initialize(workspace.ws.root_path, process_id=os.getpid())

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "textDocument/publishDiagnostics"}, remove_on_match=False
    )

    found_diagnostics_in_uris = set()
    original = message_matcher.notify

    def on_notify(msg):
        if msg is not None:
            from robocorp_ls_core import uris

            uri = msg["params"]["uri"]
            found_diagnostics_in_uris.add(os.path.basename(uris.to_fs_path(uri)))
        return original(msg)

    message_matcher.notify = on_notify

    for _i in range(2):
        found_diagnostics_in_uris.clear()
        language_server.execute_command(ROBOT_LINT_WORKSPACE, [])

        wait_for_expected_func_return(
            lambda: found_diagnostics_in_uris,
            {"root.robot", "my1.robot", "my2.robot"},
        )

    for _i in range(2):
        found_diagnostics_in_uris.clear()
        language_server.execute_command(
            ROBOT_LINT_EXPLORER,
            [None, [{"fsPath": os.path.join(workspace.ws.root_path, "sub")}]],
        )

        wait_for_expected_func_return(
            lambda: found_diagnostics_in_uris,
            {"my1.robot", "my2.robot"},
        )


def test_section_completions_integrated(language_server, ws_root_path, data_regression):
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    language_server.change_doc(uri, 2, "*settin")

    def check(expected):
        completions = language_server.get_completions(uri, 0, 7)
        del completions["id"]
        data_regression.check(completions, expected)

    check("completion_settings_plural")

    supports_language = robot_version_supports_language()

    language_server.settings(
        {
            "settings": {
                "robot": {"completions": {"section_headers": {"form": "singular"}}}
            }
        }
    )
    if supports_language:
        # Only plural form for RF 5.1
        check("completion_settings_plural")
    else:
        check("completion_settings_singular")

    language_server.settings(
        {"settings": {"robot": {"completions": {"section_headers": {"form": "both"}}}}}
    )
    if supports_language:
        # Only plural form for RF 5.1
        check("completion_settings_plural")
    else:
        check("completion_settings_both")

    language_server.settings(
        {
            "settings": {
                "robot": {"completions": {"section_headers": {"form": "plural"}}}
            }
        }
    )
    if supports_language:
        # Only plural form for RF 5.1
        check("completion_settings_plural")
    else:
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
        _check_resolve(language_server, completions["result"])
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
        _check_resolve(language_server, completions["result"])
        return completions

    data_regression.check(request_completion())

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings({"settings": {"robot": {"pythonpath": []}}})

    data_regression.check(request_completion())


def test_flow_explorer_build_model_integrated(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression
):
    from robotframework_ls.commands import ROBOT_GENERATE_FLOW_EXPLORER_MODEL

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Tasks ***
My first task
    Log     Something
    
My second task
    Log     Something
    
"""
    language_server.change_doc(uri, 2, contents)

    model = language_server.execute_command(
        ROBOT_GENERATE_FLOW_EXPLORER_MODEL, [{"uri": uri}]
    )
    data_regression.check(model["result"])


def test_flow_explorer_open_integrated(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression
):
    from robotframework_ls.commands import ROBOT_OPEN_FLOW_EXPLORER_INTERNAL
    from robocorp_ls_core import uris

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())

    Path(ws_root_path).mkdir(exist_ok=True)
    my1 = Path(ws_root_path) / "my1.robot"
    my1.write_text(
        """
*** Tasks ***
My first task
    Log     Something
    
My second task
    Log     Something
""",
        "utf-8",
    )

    my2 = Path(ws_root_path) / "my2.robot"
    my2.write_text(
        """
*** Tasks ***
My third task
    Log     Something
""",
        "utf-8",
    )

    result: ActionResultDict = language_server.execute_command(
        ROBOT_OPEN_FLOW_EXPLORER_INTERNAL,
        [
            {
                "currentFileUri": uris.from_fs_path(str(ws_root_path)),
                "htmlBundleFolderPath": ws_root_path,
            }
        ],
    )["result"]

    assert result["success"]
    uri = result["result"]
    path = uris.to_fs_path(uri)
    assert path.endswith(".html")
    assert os.path.exists(path)


def test_completions_after_library(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document
    from robotframework_ls_tests.fixtures import sort_completions
    from robotframework_ls.impl import text_utilities

    case1_path = cases.get_path("case1")

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)

    initial_source = """
*** Settings ***
Library    |

*** keywords ***
Something
    No Operation
"""
    doc = Document("")
    selected_range = text_utilities.set_doc_source_and_get_range_selected(
        initial_source, doc
    )

    language_server.change_doc(uri, 2, doc.source)

    language_server_tcp.settings({"settings": {"robot": {"pythonpath": [case1_path]}}})

    def request_completion():
        line, col = selected_range.get_end_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    completions = request_completion()["result"]
    data_regression.check(
        sort_completions(
            [
                x
                for x in completions
                if x["label"] not in ("case1_library", "$OPTIONS", "lib1", "lib2")
            ]
        )
    )


def test_completions_variable_after_library(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document
    from robotframework_ls_tests.fixtures import sort_completions

    case1_path = cases.get_path("case1")

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """
*** Settings ***
Library    curd"""
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings({"settings": {"robot": {"pythonpath": [case1_path]}}})

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    data_regression.check(sort_completions(request_completion()["result"]))


def test_completions_unicode(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, cases
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """*** Test Cases ***
Unicode
    Log    kangaroo=🦘🦘    level=INFO    """
    language_server.change_doc(uri, 2, contents)

    def request_completion():
        doc = Document("", source=contents)
        line, col = doc.get_last_line_col()
        col = convert_python_col_to_utf16_code_unit(doc, line, col)
        completions = language_server.get_completions(uri, line, col)
        del completions["id"]
        return completions

    completions = request_completion()["result"]
    for completion in completions:
        if completion["label"] == "console=":
            break
    else:
        raise AssertionError('Could not find "console=" completion.')
    text_edit = completion["textEdit"]
    doc = Document("", contents)
    doc.apply_text_edits([text_edit])
    assert (
        doc.source
        == """*** Test Cases ***
Unicode
    Log    kangaroo=🦘🦘    level=INFO    console="""
    )


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
        _check_resolve(language_server, completions["result"])
        return completions

    data_regression.check(request_completion())


def test_variables_completions_integrated(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document
    from robotframework_ls.impl.robot_version import get_robot_major_version

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

    found_options = False
    for i, completion in enumerate(completions["result"]):
        if completion["label"] == "OPTIONS":
            found_options = True
            del completions["result"][i]
            break
    assert found_options == (get_robot_major_version() >= 5)
    data_regression.check(completions, "variable_completions")

    # Note: for libraries, if we found it, we keep it in memory (so, even though
    # we removed the entry, it'll still be accessible).
    language_server_tcp.settings({"settings": {"robot": {"variables": {"myvar1": 10}}}})

    completions = language_server.get_completions(uri, line, col)
    labels = [x["label"] for x in completions["result"]]
    assert "myvar1" in labels


def test_variables_completions_integrated_using_config(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, tmpdir
):
    filename = tmpdir.join("my.txt")
    filename.write_text(
        """
-v V_NAME:value
--variable V_NAME1:value 1
--variable var2:value var2
""",
        encoding="utf-8",
    )

    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """

*** Test Cases ***
List Variable
    Should Contain    ${"""
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings(
        {"settings": {"robot": {"loadVariablesFromArgumentsFile": str(filename)}}}
    )

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()

    completions = language_server.get_completions(uri, line, col)
    labels = [x["label"] for x in completions["result"]]
    assert "V_NAME" in labels
    assert "V_NAME1" in labels
    assert "var2" in labels


def test_variablefiles_completions_integrated_using_config(
    language_server_tcp: ILanguageServerClient, ws_root_path, data_regression, tmpdir
):
    filename = tmpdir.join("my.py")
    filename.write_text(
        """
V_NAME='value'
V_NAME1='value 1'
var2='value var2'
""",
        encoding="utf-8",
    )

    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    contents = """

*** Test Cases ***
List Variable
    Should Contain    ${"""
    language_server.change_doc(uri, 2, contents)

    language_server_tcp.settings(
        {"settings": {"robot": {"loadVariablesFromVariablesFile": str(filename)}}}
    )

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()

    completions = language_server.get_completions(uri, line, col)
    labels = [x["label"] for x in completions["result"]]
    assert "V_NAME" in labels
    assert "V_NAME1" in labels
    assert "var2" in labels


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
    _check_resolve(language_server, completions["result"])
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
    _check_resolve(language_server, completions["result"])
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
    assert found[0]["targetUri"].endswith("my_library.py")


def _check_resolve(language_server: ILanguageServerClient, completions):
    for completion_item in completions:
        assert "data" in completion_item
        assert not completion_item.get("documentation")
        new_completion_item = language_server.request_resolve_completion(
            completion_item
        )["result"]
        assert "documentation" in new_completion_item
        new_completion_item.pop("data")
        completion_item.clear()
        completion_item.update(new_completion_item)


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


@pytest.mark.parametrize(
    "formatter",
    [OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY, OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY],
)
def test_code_format_integrated(
    language_server, ws_root_path, data_regression, formatter
):
    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    language_server.open_doc(uri, 1)
    language_server.settings({"settings": {"robot.codeFormatter": formatter}})
    language_server.change_doc(uri, 2, "***settings***\nDocumentation  Some doc")
    ret = language_server.request_source_format(uri)

    from robot import get_version

    version = int(get_version(naked=True).split(".")[0])
    if version >= 5:
        if formatter == OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY:
            try:
                from robot.tidy import Tidy
            except ImportError:
                pytest.skip("robot.tidy is no longer available.")
        version = "4"

    basename = "test_code_format_integrated_text_edits_" + formatter
    if formatter == OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY:
        basename += f"_{version}"
    data_regression.check(
        ret,
        basename=basename,
    )

    language_server.change_doc(uri, 3, "[Documentation]\n")
    ret = language_server.request_source_format(uri)
    assert ret["result"] == []


def test_find_definition_integrated_library(
    language_server: ILanguageServerClient, cases, workspace_dir, data_regression
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

    check_find_definition_data_regression(
        data_regression, check, basename="test_find_definition_integrated_library"
    )


def test_find_definition_keywords(
    language_server: ILanguageServerClient, cases, workspace_dir, data_regression
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
    check_find_definition_data_regression(
        data_regression, check, basename="test_find_definition_keywords"
    )


def test_find_definition_unicode(
    language_server_tcp: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Keywords ***
Keyword
    [Arguments]     ${a🦘a}    ${b🦘b}
    Log     ${b🦘b}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document("uri", txt)
    line, col = doc.get_last_line_col()
    col -= 2
    col = convert_python_col_to_utf16_code_unit(doc, line, col)

    ret = language_server.find_definitions(uri, line, col)
    assert ret["result"] == [
        {
            "originSelectionRange": {
                "start": {"character": 14, "line": 4},
                "end": {"character": 18, "line": 4},
            },
            "targetRange": {
                "start": {"character": 33, "line": 3},
                "end": {"character": 37, "line": 3},
            },
            "targetSelectionRange": {
                "start": {"character": 33, "line": 3},
                "end": {"character": 37, "line": 3},
            },
            "targetUri": "untitled:Untitled-1",
        }
    ]


def test_references_unicode(language_server_tcp: ILanguageServerClient, ws_root_path):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Keywords ***
Keyword
    [Arguments]     ${a🦘a}    ${b🦘b}
    Log     ${b🦘b}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document("uri", txt)
    line, col = doc.get_last_line_col()
    col -= 2
    col = convert_python_col_to_utf16_code_unit(doc, line, col)

    ret = language_server.request_references(uri, line, col, True)
    result = ret["result"]
    assert result == [
        {
            "uri": "untitled:Untitled-1",
            "range": {
                "start": {"line": 4, "character": 14},
                "end": {"line": 4, "character": 18},
            },
        },
        {
            "uri": "untitled:Untitled-1",
            "range": {
                "start": {"line": 3, "character": 33},
                "end": {"line": 3, "character": 37},
            },
        },
    ]


def test_selection_range_unicode(
    language_server_tcp: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Keywords ***
Keyword
    Log     ${b🦘b}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document("uri", txt)
    line, col = doc.get_last_line_col()
    col -= 2
    col = convert_python_col_to_utf16_code_unit(doc, line, col)

    ret = language_server.request_selection_range(
        uri, [{"line": line, "character": col}]
    )
    assert ret["result"] == [
        {
            "range": {
                "start": {"line": 3, "character": 14},
                "end": {"line": 3, "character": 18},
            },
            "parent": {
                "range": {
                    "start": {"line": 3, "character": 12},
                    "end": {"line": 3, "character": 19},
                },
                "parent": {
                    "range": {
                        "start": {"line": 3, "character": 4},
                        "end": {"line": 3, "character": 19},
                    },
                    "parent": {
                        "range": {
                            "start": {"line": 2, "character": 0},
                            "end": {"line": 3, "character": 19},
                        },
                        "parent": {
                            "range": {
                                "start": {"line": 1, "character": 0},
                                "end": {"line": 3, "character": 19},
                            }
                        },
                    },
                },
            },
        }
    ]


def _fix_log_signature(signatures):
    for signature in signatures:
        signature["label"] = signature["label"].replace("repr=DEPRECATED", "repr=False")
        for dct in signature["parameters"]:
            dct["label"] = dct["label"].replace("repr=DEPRECATED", "repr=False")


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
    assert docs["kind"] == MarkupKind.Markdown
    assert "Log" in docs["value"]
    _fix_log_signature(signatures)

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


def test_document_highlight_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document
    from robocorp_ls_core.lsp import DocumentHighlightResponseTypedDict
    from robocorp_ls_core.lsp import DocumentHighlightTypedDict

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Cases ***
Log It
    Log    Something
    log    Else
    """
    doc = Document("", txt)
    language_server.open_doc(uri, 1, txt)
    line, col = doc.get_last_line_col()
    line -= 1

    ret: DocumentHighlightResponseTypedDict = (
        language_server.request_text_document_highlight(uri, line, col)
    )
    result: DocumentHighlightTypedDict = ret["result"]
    assert len(result) == 2
    data_regression.check(result)


def test_document_highlight_unicode_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document
    from robocorp_ls_core.lsp import DocumentHighlightResponseTypedDict
    from robocorp_ls_core.lsp import DocumentHighlightTypedDict

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Test Cases ***
Log It
    ${a🦘a}    Set Variable    22
    log    ${a🦘a}"""
    doc = Document("", txt)
    language_server.open_doc(uri, 1, txt)
    line, col = doc.get_last_line_col()

    ret: DocumentHighlightResponseTypedDict = (
        language_server.request_text_document_highlight(uri, line, col)
    )
    result: DocumentHighlightTypedDict = ret["result"]
    assert len(result) == 2
    assert result == [
        {
            "range": {
                "start": {"line": 4, "character": 13},
                "end": {"line": 4, "character": 17},
            },
            "kind": 1,
        },
        {
            "range": {
                "start": {"line": 3, "character": 6},
                "end": {"line": 3, "character": 10},
            },
            "kind": 1,
        },
    ]


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
    from robocorp_ls_core import uris
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    language_server.settings({"settings": {"robot.codeLens.enable": True}})
    os.makedirs(ws_root_path, exist_ok=True)
    uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))

    txt = """
*** Test Case ***
Log It
    Log    

*** Task ***
Log 🦘2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_code_lens(uri)
    found = ret["result"]
    check_code_lens_data_regression(data_regression, found)


def test_code_lens_integrated_suites(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core import uris
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    language_server.settings({"settings": {"robot.codeLens.enable": True}})
    os.makedirs(ws_root_path, exist_ok=True)
    uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))
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
    check_code_lens_data_regression(data_regression, found)


def test_provide_evaluatable_expression_var_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core import uris
    from robocorp_ls_core.workspace import Document

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    os.makedirs(ws_root_path, exist_ok=True)
    uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))
    txt = """*** Test Cases ***
List Variable
    Log    ${NA🦘ME}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document(uri, txt)
    line, col = doc.get_last_line_col()

    ret = language_server.request_provide_evaluatable_expression(uri, line, col - 2)
    found = ret["result"]
    assert found == {
        "range": {
            "start": {"line": 2, "character": 13},
            "end": {"line": 2, "character": 19},
        },
        "expression": "${NA🦘ME}",
    }


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
Log 🦘2
    Log    

"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.execute_command("robot.listTests", [{"uri": uri}])
    found = ret["result"]
    data_regression.check(found)


def _fix_test_uris(tests, base_path):
    from robocorp_ls_core import uris

    base_uri = uris.from_fs_path(base_path)

    for test in tests:
        test["path"] = test["path"][len(base_path) :].replace("\\", "/")
        test["uri"] = test["uri"][len(base_uri) :].replace("\\", "/")


def test_list_tests_from_folder(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core import uris

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())

    root = Path(ws_root_path)
    root.mkdir(exist_ok=True)
    sub = root / "sub"
    sub.mkdir(exist_ok=True)
    (root / "robot1.robot").write_text(
        """
*** Test Case ***
Log It
    Log    

*** Task ***
Log It2
    Log    

""",
        encoding="utf-8",
    )

    (sub / "robot1.robot").write_text(
        """
*** Task ***
Log It2
    Log    

""",
        encoding="utf-8",
    )

    ret = language_server.execute_command(
        "robot.listTests", [{"uri": uris.from_fs_path(ws_root_path)}]
    )
    found = ret["result"]
    _fix_test_uris(found, ws_root_path)
    data_regression.check(found)


def test_rf_info_integrated(
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

    ret = language_server.execute_command("robot.rfInfo.internal", [{"uri": uri}])
    found = ret["result"]
    assert isinstance(found, dict)
    assert int(found["version"].split(".")[0]) >= 3
    assert found["python"] == sys.executable


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


def test_rename_integrated(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Keywords ***
Keyword
    [Arguments]     ${foo}    ${bar}=${foo}
    Log     ${foo}"""
    language_server.open_doc(uri, 1, txt)

    line, col = Document("uri", txt).get_last_line_col()

    ret = language_server.request_rename(uri, line, col - 2, "newName")
    data_regression.check(ret["result"]["changes"])


def test_rename_integrated_unicode(
    language_server_io: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """
*** Keywords ***
Keyword
    [Arguments]     ${foooo}
    Log     kangaroo=🦘🦘    level=INFO    ${foooo}
    Log     kangaroo=🦘🦘    level=INFO    ${foooo}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document("uri", txt)
    line, col = doc.get_last_line_col()
    col -= 2
    col = convert_python_col_to_utf16_code_unit(doc, line, col)

    ret = language_server.request_rename(uri, line, col - 2, "newName")

    workspace_edit: WorkspaceEditTypedDict = ret["result"]

    changes = workspace_edit["changes"]
    text_edits: List[TextEditTypedDict] = changes[uri]
    doc.apply_text_edits(text_edits)
    expected = txt.replace("${foooo}", "${newName}")
    assert doc.source == expected


def test_rename_integrated_unicode_2(
    language_server_io: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """*** Test Cases ***
Unicode
    ${a🦘a}=    Set Variable    22
    Log    ${a🦘a}"""
    language_server.open_doc(uri, 1, txt)

    doc = Document("uri", txt)
    line, col = doc.get_last_line_col()
    col -= 3
    col = convert_python_col_to_utf16_code_unit(doc, line, col)

    ret = language_server.request_prepare_rename(uri, line, col)
    range_found = ret["result"]
    assert range_found == {
        "start": {"line": 3, "character": 13},
        "end": {"line": 3, "character": 17},
    }


def test_code_action_unicode_integrated(
    language_server_io: ILanguageServerClient, ws_root_path
):
    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    uri = "untitled:Untitled-1"
    txt = """*** Test Cases ***
Unicode
    Log    a🦘🦘a"""
    language_server.open_doc(uri, 1, txt)

    line = 2
    # select a🦘|🦘a|
    col = 14
    endcol = 17

    ret = language_server.request_code_action(uri, line, col, line, endcol)
    found = ret["result"]
    found = [x for x in found if x["command"]["title"] == "Extract local variable"]
    assert found == [
        {
            "title": "Extract local variable",
            "kind": "refactor.extract",
            "command": {
                "title": "Extract local variable",
                "command": "robot.applyCodeAction",
                "arguments": [
                    {
                        "apply_snippet": {
                            "edit": {
                                "changes": {
                                    "untitled:Untitled-1": [
                                        {
                                            "range": {
                                                "start": {"line": 2, "character": 0},
                                                "end": {"line": 2, "character": 0},
                                            },
                                            "newText": "    ${${0:variable}}=    Set Variable    🦘a\n",
                                        },
                                        {
                                            "range": {
                                                "start": {"line": 2, "character": 14},
                                                "end": {"line": 2, "character": 17},
                                            },
                                            "newText": "${${0:variable}}",
                                        },
                                    ]
                                }
                            },
                            "label": "Extract local variable",
                        }
                    }
                ],
            },
        }
    ]


def test_shadowing_libraries(language_server_io: ILanguageServerClient, workspace_dir):
    from robocorp_ls_core import uris
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
        assert message_matcher

        language_server.open_doc(uri1, 1, text=None)
        assert message_matcher.event.wait(TIMEOUT)
        assert message_matcher.msg["params"]["uri"] == uri1
        assert message_matcher.msg["params"]["diagnostics"] == []

        message_matcher = language_server.obtain_pattern_message_matcher(
            {"method": "textDocument/publishDiagnostics"}
        )
        assert message_matcher

        language_server.open_doc(uri2, 1, text=None)
        assert message_matcher.event.wait(TIMEOUT)
        assert message_matcher.msg["params"]["uri"] == uri2
        assert message_matcher.msg["params"]["diagnostics"] == []

        language_server.close_doc(uri2)
        language_server.close_doc(uri1)


class _RfInterpreterInfo:
    def __init__(self, interpreter_id: int, uri: str):
        self.interpreter_id = interpreter_id
        self.uri = uri


@pytest.fixture
def rf_interpreter_startup(language_server_io: ILanguageServerClient, ws_root_path):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_START
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_STOP
    from robocorp_ls_core import uris

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    os.makedirs(ws_root_path, exist_ok=True)
    uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))

    ret1 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_START, [{"uri": uri}]
    )
    assert ret1["result"] == {
        "success": True,
        "message": None,
        "result": {"interpreter_id": 0},
    }
    yield _RfInterpreterInfo(interpreter_id=0, uri=uri)
    # Note: success could be False if it was stopped in the test...
    language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 0}]
    )


def test_rf_interactive_integrated_basic(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_START
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_STOP
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS
    from robocorp_ls_core.lsp import Position

    language_server = language_server_io
    uri = rf_interpreter_startup.uri

    ret2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_START, [{"uri": uri}]
    )
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
    assert message_matcher
    eval2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        [
            {
                "interpreter_id": 1,
                "code": (
                    "\r"
                    "*** Task ***\r"
                    "Some task\r"
                    "    Log    Something     console=True\r"
                ),
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

    completions = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        [{"interpreter_id": 1, "code": "Lo", "position": Position(0, 2).to_dict()}],
    )

    for completion in completions["result"]["suggestions"]:
        if completion["label"] == "Log (BuiltIn)":
            break
    else:
        raise AssertionError('Did not find "Log" in the suggestions.')

    stop2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 1}]
    )
    assert stop2["result"] == {"success": True, "message": None, "result": None}


def test_rf_interactive_integrated_input_request(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE
    from robocorp_ls_core import uris

    language_server = language_server_io
    uri = rf_interpreter_startup.uri
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

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "interpreter/output"}
    )
    assert message_matcher
    language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        [{"interpreter_id": 0, "code": "*** Settings ***\nLibrary    ./my_lib.py"}],
    )

    def run_in_thread():
        language_server.execute_command(
            ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
            [
                {
                    "interpreter_id": 0,
                    "code": """
*** Test Case ***
Test
    ${var}=  Check Input
    Log    ${var}     console=True
""",
                }
            ],
        )

    t = threading.Thread(target=run_in_thread)
    t.start()

    assert message_matcher.event.wait(10)
    assert message_matcher.msg == {
        "jsonrpc": "2.0",
        "method": "interpreter/output",
        "params": {
            "output": "Enter something\n",
            "category": "stdout",
            "interpreter_id": 0,
        },
    }
    import time

    time.sleep(0.5)

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "interpreter/output"}
    )
    assert message_matcher

    language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        [{"interpreter_id": 0, "code": "EnterThis"}],
    )
    assert message_matcher.event.wait(10)
    assert message_matcher.msg == {
        "jsonrpc": "2.0",
        "method": "interpreter/output",
        "params": {"output": "EnterThis\n", "category": "stdout", "interpreter_id": 0},
    }

    t.join(10)
    assert not t.is_alive()


def test_rf_interactive_integrated_hook_robocorp_update_env(
    language_server_io: ILanguageServerClient, cases: CasesFixture, workspace_dir: str
):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE
    from robocorp_ls_core import uris
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_START

    language_server = language_server_io

    cases.copy_to("custom_env", workspace_dir)

    p = Path(workspace_dir)
    plugins_path = p / "plugins"
    assert plugins_path.exists()
    language_server.initialize(
        workspace_dir,
        process_id=os.getpid(),
        initialization_options={
            "pluginsDir": str(plugins_path),
            "integrationOption": "robocorp",
        },
    )

    p = Path(workspace_dir) / "env1" / "caselib1.robot"
    assert p.exists()

    uri = uris.from_fs_path(str(p))

    handled_update_launch_env = threading.Event()

    def handle_execute_workspace_command(method, message_id, params):
        assert method == "$/executeWorkspaceCommand"
        assert isinstance(params, dict)

        command = params["command"]
        assert command == "robocorp.updateLaunchEnv"

        arguments = params["arguments"]
        assert arguments["targetRobot"]
        env = arguments["env"]
        env["CUSTOM_VAR_SET_FROM_TEST"] = "EXPECTED VALUE"

        contents = {"jsonrpc": "2.0", "id": message_id, "result": env}
        language_server.write(contents)
        handled_update_launch_env.set()
        return True

    language_server.register_request_handler(
        "$/executeWorkspaceCommand", handle_execute_workspace_command
    )

    ret1 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_START, [{"uri": uri}]
    )
    assert handled_update_launch_env.wait(5)
    try:
        assert ret1["result"] == {
            "success": True,
            "message": None,
            "result": {"interpreter_id": 0},
        }

        message_matcher_interpreter_output = (
            language_server.obtain_pattern_message_matcher(
                {"method": "interpreter/output"}
            )
        )
        assert message_matcher_interpreter_output

        def run_in_thread():
            language_server.execute_command(
                ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
                [
                    {
                        "interpreter_id": 0,
                        "code": """
*** Test Case ***
Test
    Log to console   %{CUSTOM_VAR_SET_FROM_TEST}
""",
                    }
                ],
            )

        t = threading.Thread(target=run_in_thread)
        t.start()

        assert message_matcher_interpreter_output.event.wait(10)
        assert message_matcher_interpreter_output.msg == {
            "jsonrpc": "2.0",
            "method": "interpreter/output",
            "params": {
                "output": "EXPECTED VALUE\n",
                "category": "stdout",
                "interpreter_id": 0,
            },
        }

    finally:
        # Note: success could be False if it was stopped in the test...
        language_server.execute_command(
            ROBOT_INTERNAL_RFINTERACTIVE_STOP, [{"interpreter_id": 0}]
        )


def test_rf_interactive_integrated_completions(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
):
    from robotframework_ls.commands import (
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
    )
    from robocorp_ls_core.lsp import Position

    language_server = language_server_io
    completions = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        [
            {
                "interpreter_id": rf_interpreter_startup.interpreter_id,
                "code": "\n\nLo",
                "position": Position(2, 2).to_dict(),
            }
        ],
    )

    for completion in completions["result"]["suggestions"]:
        if completion["label"] == "Log (BuiltIn)":
            assert "documentation" not in completion
            completion = language_server.execute_command(
                ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
                [
                    {
                        "interpreter_id": rf_interpreter_startup.interpreter_id,
                        "completionItem": completion,
                    }
                ],
            )["result"]

            assert completion.pop("documentation")["value"].startswith("**Log(")
            del completion["data"]
            assert completion == {
                "label": "Log (BuiltIn)",
                "kind": 0,
                "insertText": "Log    ${1:message}",
                "insertTextRules": 4,
                "range": {
                    "start": {"line": 5, "character": 4},
                    "end": {"line": 5, "character": 6},
                    "startLineNumber": 3,
                    "startColumn": 1,
                    "endLineNumber": 3,
                    "endColumn": 3,
                },
            }
            break
    else:
        raise AssertionError('Did not find "Log" in the suggestions.')


def test_rf_interactive_integrated_completions_not_duplicated(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
):
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS
    from robocorp_ls_core.lsp import Position
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE

    language_server = language_server_io

    eval2 = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
        [
            {
                "interpreter_id": rf_interpreter_startup.interpreter_id,
                "code": """
*** Keyword ***
Mykeywordentered
    Log    Something     console=True
    
*** Keyword ***
Mykeywordentered
    Log    Something     console=True
""",
            }
        ],
    )
    assert eval2["result"] == {"success": True, "message": None, "result": None}

    completions = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        [
            {
                "interpreter_id": rf_interpreter_startup.interpreter_id,
                "code": "\n\nMykeyworde",
                "position": Position(2, 2).to_dict(),
            }
        ],
    )

    assert len(completions["result"]["suggestions"]) == 1


def test_rf_interactive_integrated_fs_completions(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
    data_regression,
):
    from robocorp_ls_core import uris
    from robocorp_ls_core.workspace import Document

    # Check that we're able to get completions based on the current dir.
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS
    from robocorp_ls_core.lsp import Position

    uri = rf_interpreter_startup.uri
    fs_path = uris.to_fs_path(uri)
    dirname = os.path.dirname(fs_path)
    with open(os.path.join(dirname, "my_lib_03.py"), "w") as stream:
        stream.write(
            """
def some_method():
    pass
"""
        )

    language_server = language_server_io
    code = "*** Settings ***\nLibrary    ./my_"
    doc = Document(uri, code)
    completions = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        [
            {
                "interpreter_id": rf_interpreter_startup.interpreter_id,
                "code": code,
                "position": Position(*doc.get_last_line_col()).to_dict(),
            }
        ],
    )

    suggestions = completions["result"]["suggestions"]
    assert suggestions
    data_regression.check(suggestions)


def test_rf_interactive_integrated_auto_import_completions(
    language_server_io: ILanguageServerClient,
    rf_interpreter_startup: _RfInterpreterInfo,
    data_regression,
):
    from robocorp_ls_core.workspace import Document
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression
    from robotframework_ls.commands import (
        ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
    )
    from robocorp_ls_core.lsp import CompletionItemTypedDict
    from robocorp_ls_core.lsp import MonacoMarkdownStringTypedDict

    # Check that we're able to get completions based on the current dir.
    from robotframework_ls.commands import ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS
    from robocorp_ls_core.lsp import Position

    uri = rf_interpreter_startup.uri

    language_server = language_server_io
    code = "append to lis"
    doc = Document(uri, code)
    completions = language_server.execute_command(
        ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
        [
            {
                "interpreter_id": rf_interpreter_startup.interpreter_id,
                "code": code,
                "position": Position(*doc.get_last_line_col()).to_dict(),
            }
        ],
    )

    suggestions = completions["result"]["suggestions"]
    assert suggestions
    assert "documentation" not in suggestions[0]
    new_completion_item = typing.cast(
        CompletionItemTypedDict,
        language_server.execute_command(
            ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
            [
                {
                    "interpreter_id": rf_interpreter_startup.interpreter_id,
                    "completionItem": suggestions[0],
                }
            ],
        )["result"],
    )

    assert "documentation" in new_completion_item
    documentation = typing.cast(
        MonacoMarkdownStringTypedDict, new_completion_item["documentation"]
    )

    # Check for the version where docutils is installed or not.
    if "Adds `values` to the end of `list`" not in documentation["value"]:
        assert "Adds values to the end of" in documentation["value"]

    new_completion_item["documentation"] = "<replaced_for_test>"
    del new_completion_item["data"]
    check_code_lens_data_regression(data_regression, [new_completion_item])


def test_code_lens_integrated_rf_interactive(
    language_server_io: ILanguageServerClient, ws_root_path, data_regression
):
    from robocorp_ls_core import uris
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression

    language_server = language_server_io

    language_server.initialize(ws_root_path, process_id=os.getpid())
    language_server.settings({"settings": {"robot.codeLens.enable": True}})
    uri_untitled = "~untitled"
    txt = """
*** Task ***
Log It
    Log
"""
    language_server.open_doc(uri_untitled, 1, txt)
    ret = language_server.request_code_lens(uri_untitled)
    found = ret["result"]
    assert not found  # when unable to resolve path, we can't create it.

    os.makedirs(ws_root_path, exist_ok=True)
    uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))
    txt = """
*** Task ***
Log It
    Log
"""
    language_server.open_doc(uri, 1, txt)

    ret = language_server.request_code_lens(uri)
    found = ret["result"]
    for code_lens in found:
        if code_lens.get("data", {}).get("type") == "rf_interactive":
            break
    else:
        raise AssertionError(f"Unable to find 'rf_interactive' code lens in: {ret}")
    check_code_lens_data_regression(
        data_regression, [code_lens], basename="code_lens_before_resolve"
    )

    ret = language_server.request_resolve_code_lens(code_lens)
    resolved_code_lens = ret["result"]
    check_code_lens_data_regression(
        data_regression, [resolved_code_lens], basename="code_lens_after_resolve"
    )


def test_get_rfls_home_dir(language_server_io: ILanguageServerClient):
    assert language_server_io.execute_command("robot.getRFLSHomeDir", [])[
        "result"
    ].endswith(".robotframework-ls")


def test_cancelling_requests(language_server_tcp: ILanguageServerClient, ws_root_path):
    from robotframework_ls.impl.robot_version import get_robot_major_version

    if get_robot_major_version() <= 3:
        raise pytest.skip(reason="This test is brittle in RF 3.")

    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp

    language_server.initialize(ws_root_path, process_id=os.getpid())

    uri = "~untitled"
    contents = []

    # Let's create a document with many keywords so that it's somewhat slow to parse.
    for i in range(500):
        contents.append(
            f"""
*** Keyword ***
Some keyword {i}
    Log to console    Something
    Log to console    Something
    Log to console    Something
    Log to console    Something
    Log to console    Something
    Log to console    Something
    

"""
        )

    contents.append(
        """
*** Keyword ***
Another keyword
    Log to cons"""
    )
    txt = "".join(contents)

    language_server.open_doc(uri, 1, txt)

    doc = Document("", source=txt)
    line, col = doc.get_last_line_col()
    completions_message_matcher = language_server.get_completions_async(uri, line, col)
    assert completions_message_matcher

    language_server.request_cancel(completions_message_matcher.message_id)

    timeout = 10
    if not completions_message_matcher.event.wait(timeout=timeout):
        raise TimeoutError(f"Request timed-out: ({timeout}s)")

    assert completions_message_matcher.msg["error"]["message"] == "Request Cancelled"


def test_collect_robot_documentation(
    language_server_tcp: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp
    language_server.initialize(ws_root_path, process_id=os.getpid())

    uri = "unnamed"
    language_server.open_doc(uri, 1)
    contents = """
*** Settings ***
Library    Collections

*** Keyword ***
My keyword
    Append to list"""
    language_server.change_doc(uri, 2, contents)

    doc = Document(uri, contents)

    found = language_server.execute_command(
        "robot.collectRobotDocumentation", [{"library_name": "BuiltIn"}]
    )["result"]
    assert not found["success"]
    assert found["message"] == "uri not provided"

    found = language_server.execute_command(
        "robot.collectRobotDocumentation", [{"uri": uri, "library_name": "BuiltIn"}]
    )["result"]
    assert found["success"], f"Found: {found}"
    assert found["result"]["libdoc_json"]["name"] == "BuiltIn"

    line, col = doc.get_last_line_col_with_contents("Library    Collections")

    # Generate it for Collections
    found = language_server.execute_command(
        "robot.collectRobotDocumentation", [{"uri": uri, "line": line, "col": col}]
    )["result"]
    assert found["success"], f"Found: {found}"
    assert found["result"]["libdoc_json"]["name"] == "Collections"

    line, col = doc.get_last_line_col_with_contents("*** Keyword ***")
    found = language_server.execute_command(
        "robot.collectRobotDocumentation", [{"uri": uri, "line": line, "col": col}]
    )["result"]
    assert not found["success"], f"Found: {found}"
    assert "No custom documentation available for" in found["message"]


def test_dependency_graph_integration_base(
    language_server_tcp: ILanguageServerClient, ws_root_path
):
    from robocorp_ls_core import uris
    from robocorp_ls_core.workspace import Document

    language_server = language_server_tcp

    language_server.initialize(ws_root_path, process_id=os.getpid())
    internal_my_uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))
    internal_resource_uri = uris.from_fs_path(
        os.path.join(ws_root_path, "shared.resource")
    )

    if sys.platform == "win32":

        def to_vscode_uri(initial_uri):
            assert initial_uri.startswith("file:///")
            # Make something as:
            # file:///c:/Users/f
            # into
            # file:///C%3A/Users/f
            # -- note: when normalized it's still the same
            uri = initial_uri[:8] + initial_uri[8].upper() + "%3A" + initial_uri[10:]
            assert uris.normalize_uri(uri) == initial_uri
            return uri

    else:

        def to_vscode_uri(uri):
            return uri

    uri_my = to_vscode_uri(internal_my_uri)
    uri_resource = to_vscode_uri(internal_resource_uri)

    next_id: "partial[int]" = partial(next, itertools.count())

    language_server.open_doc(uri_resource, next_id())

    language_server.open_doc(uri_my, next_id())
    contents = """
*** Settings ***
Resource    shared.resource

*** Keyword ***
My keyword
    Append to list"""
    language_server.change_doc(uri_my, next_id(), contents)

    doc = Document("", source=contents)
    line, col = doc.get_last_line_col()
    completions = language_server.get_completions(uri_my, line, col)
    # I.e.: show only completion which adds import
    found = [
        c
        for c in completions["result"]
        if c["label"] == "Append To List (Collections)*"
    ]
    assert len(found) == 1
    found = [
        c for c in completions["result"] if c["label"] == "Append To List (Collections)"
    ]
    assert len(found) == 0

    language_server.change_doc(
        uri_resource,
        next_id(),
        """
*** Settings ***
Library    Collections
""",
    )

    completions = language_server.get_completions(uri_my, line, col)
    # I.e.: Don't show completion which adds import (show only the one
    # which is already in the context).
    found = [
        c
        for c in completions["result"]
        if c["label"] == "Append To List (Collections)*"
    ]
    assert len(found) == 0

    found = [
        c for c in completions["result"] if c["label"] == "Append To List (Collections)"
    ]
    assert len(found) == 1


# def test_dependency_graph_integration_lint(
#     language_server_tcp: ILanguageServerClient, ws_root_path
# ):
#     from robocorp_ls_core import uris
#     import sys
#     from robocorp_ls_core.workspace import Document
#
#     language_server = language_server_tcp
#
#     language_server.initialize(ws_root_path, process_id=os.getpid())
#     internal_my_uri = uris.from_fs_path(os.path.join(ws_root_path, "my.robot"))
#     internal_resource_uri = uris.from_fs_path(
#         os.path.join(ws_root_path, "shared.resource")
#     )
#
#     if sys.platform == "win32":
#
#         def to_vscode_uri(initial_uri):
#             assert initial_uri.startswith("file:///")
#             # Make something as:
#             # file:///c:/Users/f
#             # into
#             # file:///C%3A/Users/f
#             # -- note: when normalized it's still the same
#             uri = initial_uri[:8] + initial_uri[8].upper() + "%3A" + initial_uri[10:]
#             # assert uris.normalize_uri(uri) == initial_uri
#             return uri
#
#     else:
#
#         def to_vscode_uri(uri):
#             return uri
#
#     uri_my = to_vscode_uri(internal_my_uri)
#     uri_resource = to_vscode_uri(internal_resource_uri)
#
#     next_id: "partial[int]" = partial(next, itertools.count())
#
#     message_matcher = language_server.obtain_pattern_message_matcher(
#         {"method": "textDocument/publishDiagnostics"}
#     )
#
#     language_server.open_doc(uri_resource, next_id())
#
#     language_server.open_doc(uri_my, next_id())
#     contents = """
# *** Settings ***
# Resource    shared.resource
#
# *** Keyword ***
# My keyword
#     Append to lis"""
#     language_server.change_doc(uri_my, next_id(), contents)
#
#     from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT
#     from robotframework_ls_tests.fixtures import sort_diagnostics
#
#     assert message_matcher.event.wait(TIMEOUT)
#
#     message_matcher = language_server.obtain_pattern_message_matcher(
#         {"method": "textDocument/publishDiagnostics"}
#     )
#     assert message_matcher.event.wait(TIMEOUT)
#     diag = message_matcher.msg["params"]
#     print(diag)
#
#     doc = Document("", source=contents)
#     line, col = doc.get_last_line_col()
#     completions = language_server.get_completions(uri_my, line, col)
#     # I.e.: show only completion which adds import
#     found = [
#         c
#         for c in completions["result"]
#         if c["label"] == "Append To List (Collections)*"
#     ]
#     assert len(found) == 1
#     found = [
#         c for c in completions["result"] if c["label"] == "Append To List (Collections)"
#     ]
#     assert len(found) == 0
#
#     language_server.change_doc(
#         uri_resource,
#         next_id(),
#         """
# *** Settings ***
# Library    Collections
# """,
#     )
#
#     completions = language_server.get_completions(uri_my, line, col)
#     # I.e.: Don't show completion which adds import (show only the one
#     # which is already in the context).
#     found = [
#         c
#         for c in completions["result"]
#         if c["label"] == "Append To List (Collections)*"
#     ]
#     assert len(found) == 0
#
#     found = [
#         c for c in completions["result"] if c["label"] == "Append To List (Collections)"
#     ]
#     assert len(found) == 1
#
