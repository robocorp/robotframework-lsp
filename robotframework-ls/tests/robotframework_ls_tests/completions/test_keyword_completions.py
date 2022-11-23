import pytest
from robotframework_ls.impl.protocols import ICompletionContext
import sys


def test_keyword_completions_builtin(workspace, libspec_manager):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    should be")

    _check_should_be_completions(doc, workspace.ws)


def test_keyword_completions_format(workspace, libspec_manager):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT,
        OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_FIRST_UPPER,
    )
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    should be")

    config = RobotConfig()
    config.update(
        {
            OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT: OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_FIRST_UPPER
        }
    )
    assert (
        config.get_setting(OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT, str, "")
        == OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_FIRST_UPPER
    )

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "Length should be (BuiltIn)",
        "Should be empty (BuiltIn)",
        "Should be equal (BuiltIn)",
        "Should be equal as integers (BuiltIn)",
        "Should be equal as numbers (BuiltIn)",
        "Should be equal as strings (BuiltIn)",
        "Should be true (BuiltIn)",
    ]


@pytest.mark.parametrize("separator", ("${/}", "/", "\\"))
@pytest.mark.parametrize("use_config", (True, False))
def test_keyword_completions_directory_separator(
    workspace, libspec_manager, use_config, separator
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig

    if sys.platform != "win32" and separator == "\\":
        return

    workspace.set_root("case_inner_keywords", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = f"""
*** Settings ***
Resource    inner{separator}case_inner.robot


*** Test Cases ***
Testing Completion Here
    Check with ke"""

    if use_config:
        config = RobotConfig()
    else:
        config = None

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "Check with keyword at inner (case_inner)"
    ]


def test_keyword_completions_builtin_after_space(workspace, libspec_manager):
    from robocorp_ls_core.protocols import IDocument

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc: IDocument = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    should be ")

    _check_should_be_completions(doc, workspace.ws)


def test_keyword_completions_builtin_after_space_before_newline(
    workspace, libspec_manager
):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    should be \n")

    line, _col = doc.get_last_line_col()
    line_contents = doc.get_line(line - 1)

    _check_should_be_completions(
        doc, workspace.ws, line=line - 1, col=len(line_contents)
    )


def _check_resolve(context: ICompletionContext, completions):
    for completion_item in completions:
        data = completion_item.pop("data", None)
        assert data
        assert not completion_item.get("documentation")
        context.resolve_completion_item(data, completion_item)
        assert "documentation" in completion_item


def test_keyword_completions_changes_user_library(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    import time
    from os.path import os

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    verify")

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(completions, basename="keyword_completions_1")

    time.sleep(1)  # Make sure that the mtime changes enough in the filesystem

    library_py = os.path.join(workspace_dir, "case1_library.py")
    with open(library_py, "r") as stream:
        contents = stream.read()

    contents += """
def verify_changes(model=10):
    pass
"""
    with open(library_py, "w") as stream:
        stream.write(contents)
    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    assert sorted(completion["label"] for completion in completions) == [
        "Verify Another Model (case1_library)",
        "Verify Changes (case1_library)",
        "Verify Model (case1_library)",
    ]


@pytest.mark.parametrize(
    "library_import", ["case1_library", "case1_library.py", "__FULL_PATH__"]
)
def test_keyword_completions_user_library(
    data_regression, workspace, cases, libspec_manager, library_import, workspace_dir
):
    import os.path
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robocorp_ls_core import uris

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")

    if library_import == "__FULL_PATH__":
        case1_robot_path = uris.to_fs_path(doc.uri)
        case1_py_path = os.path.join(
            os.path.dirname(case1_robot_path), "case1_library.py"
        )
        library_import = case1_py_path

    new_source = doc.source.replace("case1_library", library_import)
    new_source = new_source + "\n    verify"
    doc = workspace.put_doc("case1.robot", new_source)

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(completions, basename="keyword_completions_1")

    # Now, let's put a .libspec file in the workspace and check whether
    # it has priority over the auto-generated spec file.
    with open(os.path.join(workspace_dir, "new_spec.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.synchronize_workspace_folders()

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(completions, basename="keyword_completions_2_new")


@pytest.mark.parametrize("contents", ["\n    case1_library.", "\n    case1 library."])
def test_keyword_completions_case1(
    data_regression, workspace, cases, libspec_manager, workspace_dir, contents
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + contents)

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(completions, basename="keyword_completions_1_all")


def test_keyword_completions_user_in_robot_file(
    data_regression, workspace, cases, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root(cases.get_path("case2"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc("case2.robot", doc.source + "\n    my equ")

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(
        completions, basename="keyword_completions_user_in_robot_file"
    )


def test_keyword_completions_from_resource_files(
    data_regression, workspace, tmpdir, cases, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES
    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    config.update({"robot": {"variables": {"ext_folder": cases.get_path("ext")}}})
    assert config.get_setting(OPTION_ROBOT_VARIABLES, dict, {}) == {
        "ext_folder": cases.get_path("ext")
    }

    workspace.set_root(cases.get_path("case3"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case3.robot")
    doc = workspace.put_doc("case3.robot", doc.source + "\n    equal redef")

    context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    data_regression.check(
        completions, basename="keyword_completions_from_resource_files"
    )


def test_keyword_completions_from_recursively_included_resource_files(
    data_regression, workspace, cases, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root(cases.get_path("case4"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc("case4.robot", doc.source + "\n    equal redef")

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(
        completions, basename="keyword_completions_from_recursively_resource_files"
    )


def test_keyword_completions_builtin_duplicated(workspace, cases, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root(cases.get_path("case4"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc("case4.robot", doc.source + "\n    should be equal")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "should be equal (builtin)"
    ]

    assert len(found) == 1, f'Found: {[x["label"] for x in completions]}'


def test_keyword_completions_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot", doc.source + "\n    [Teardown]    my_Equal red"
    )

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "my equal redefined (case2)"
    ]

    assert len(found) == 1, f'Found: {[x["label"] for x in completions]}'


def test_keyword_completions_settings_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot", doc.source + "\n*** Keywords ***\nTeardown    my_Equal red"
    )

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "my equal redefined (case2)"
    ]

    assert len(found) == 1, f'Found: {[x["label"] for x in completions]}'


def test_keyword_completions_bdd_prefix(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot", doc.source + "\n*** Keywords ***\nTeardown    WHEN my_Equal red"
    )

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    found = [
        completion
        for completion in completions
        if completion["label"].lower() == "my equal redefined (case2)"
    ]
    assert len(found) == 1, f'Found: {[x["label"] for x in completions]}'
    data_regression.check(found)


def test_keyword_completions_template(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Settings ***
Test Template    my eq"""

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "my equal redefined (case2)"
    ]

    assert len(found) == 1, f'Found: {[x["label"] for x in completions]}'


def test_keyword_completions_resource_does_not_exist(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")

    doc.source = """*** Settings ***
Library    DoesNotExist
Library    .
Library    ..
Library    ../
Resource    does_not_exist.txt
Resource    ${foo}/does_not_exist.txt
Resource    ../does_not_exist.txt
Resource    .
Resource    ..
Resource    ../
Resource    ../../does_not_exist.txt
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3."""

    config = RobotConfig()
    context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(completions)


def test_keyword_completions_library_prefix(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")

    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3."""

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(
        completions, basename="test_keyword_completions_library_prefix_1"
    )

    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3.Another"""

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(
        completions, basename="test_keyword_completions_library_prefix_2"
    )

    doc.source = """*** Settings ***
Library    Collections

*** Test Cases ***
Test
    Collections.Append To Lis"""

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)
    assert [completion["label"] for completion in completions] == [
        "Append To List (Collections)"
    ]


def test_keyword_completions_with_stmt(workspace, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")

    doc.source = """*** Settings ***
Library    Collections    WITH NAME    Col1

*** Test Cases ***
Test
    Col1.Append To Lis"""

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert [completion["label"] for completion in completions] == [
        "Append To List (Col1)"
    ]


def test_keyword_completions_respect_pythonpath(
    workspace, cases, libspec_manager, data_regression
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    case4_path = cases.get_path("case4")

    # Note how we are accessing case4resource.txt while the workspace is set for case3.

    config = RobotConfig()
    config.update({"robot": {"pythonpath": [case4_path]}})
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [case4_path]
    libspec_manager.config = config

    workspace.set_root(cases.get_path("case3"), libspec_manager=libspec_manager)
    doc = workspace.put_doc("case3.robot")
    doc.source = """*** Settings ***
Resource    case4resource.txt

*** Test Cases ***
Can use resource keywords
    [Documentation]      Checks that we can have a resource
    ...                  including another resource.
    My Equal Redefined   2   2
    Yet Another Equ"""

    context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(completions)


def test_typing_not_shown(libspec_manager, workspace, data_regression, workspace_dir):
    from robocorp_ls_core import uris
    from os.path import os
    from robotframework_ls_tests.fixtures import LIBSPEC_3
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robocorp_ls_core.lsp import TextDocumentItem

    workspace_dir_a = os.path.join(workspace_dir, "workspace_dir_a")
    os.makedirs(workspace_dir_a)
    with open(os.path.join(workspace_dir_a, "my.libspec"), "w") as stream:
        stream.write(LIBSPEC_3)
    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)

    doc = workspace.ws.put_document(TextDocumentItem("temp_doc.robot", text=""))
    assert (
        libspec_manager.get_library_doc_or_error(
            "case3_library",
            False,
            CompletionContext(
                doc,
                workspace=workspace.ws,
            ),
        ).library_doc
        is not None
    )

    doc.source = """*** Settings ***
Library    case3_library

*** Test Cases ***
Can use resource keywords
    Case Verify"""

    context = CompletionContext(doc, workspace=workspace.ws)
    completions = keyword_completions.complete(context)
    _check_resolve(context, completions)

    data_regression.check(completions)


def test_keyword_completions_circular_imports(workspace, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case_circular", libspec_manager=libspec_manager)
    doc = workspace.get_doc("main.robot")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "My Keyword 1 (keywords1)",
        "My Keyword 2 (keywords2)",
    ]


def test_keyword_completions_lib_with_params(workspace, libspec_manager, cases):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib.robot")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert sorted([comp["label"] for comp in completions]) == ["Foo Method (Lib)"]


def test_keyword_completions_lib_with_params_slash(workspace, libspec_manager, cases):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib2.robot")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config)
    )
    if sys.platform == "win32":
        expected = r"My:\foo\bar\echo (LibWithParams2)"
    else:
        expected = r"My:\foo\bar/echo (LibWithParams2)"

    assert sorted([comp["label"] for comp in completions]) == [expected]


def test_simple_with_params(workspace, libspec_manager, cases):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib.robot")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert sorted([comp["label"] for comp in completions]) == ["Foo Method (Lib)"]


def _check_should_be_completions(doc, ws, **kwargs):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    completion_context = CompletionContext(doc, workspace=ws, **kwargs)

    completions = keyword_completions.complete(completion_context)
    assert sorted([comp["label"] for comp in completions]) == [
        "Length Should Be (BuiltIn)",
        "Should Be Empty (BuiltIn)",
        "Should Be Equal (BuiltIn)",
        "Should Be Equal As Integers (BuiltIn)",
        "Should Be Equal As Numbers (BuiltIn)",
        "Should Be Equal As Strings (BuiltIn)",
        "Should Be True (BuiltIn)",
    ]


def test_keyword_completions_on_keyword_arguments(workspace, libspec_manager):

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot", doc.source + "\n    Run keyword if    ${var}    Should Be"
    )
    _check_should_be_completions(doc, workspace.ws)


def test_keyword_completions_on_keyword_arguments_run_keyword_if(
    workspace, libspec_manager
):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
        doc.source
        + "\n    Run keyword if    ${var}    No Operation    ELSE IF   ${cond}    Should Be",
    )

    _check_should_be_completions(doc, workspace.ws)


def test_keyword_completions_on_wait_until_keyword_succeeds(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Some defined keyword
    [Arguments]    ${foo}    ${bar}

    Log To Console    ${foo} ${bar}
    
ret
    ${ret}=    Wait Until Keyword Succeeds    5m    10s    Some defin"""
    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    for c in completions:
        c.pop("data", None)
    data_regression.check(completions)


def test_keyword_completions_on_wait_until_keyword_succeeds_with_params(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Some defined keyword
    [Arguments]    ${foo}    ${bar}

    Log To Console    ${foo} ${bar}
    
ret
    ${ret}=    Wait Until Keyword Succeeds    5m    10s    Some defined keyword    f"""
    completions = complete_all(CompletionContext(doc, workspace=workspace.ws))
    data_regression.check(completions)


def test_keyword_completions_on_wait_until_keyword_succeeds_with_params_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Some defined keyword
    [Arguments]    ${foo}    ${bar}

    Log To Console    ${foo} ${bar}
    
ret
    ${ret}=    Wait Until Keyword Succeeds    5m    10s    Some defined keyword    """
    completions = complete_all(CompletionContext(doc, workspace=workspace.ws))
    data_regression.check(completions)


def test_keyword_completions_on_keyword_arguments_run_keyword_if_space_at_end(
    workspace, libspec_manager
):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
        doc.source
        + "\n    Run keyword if    ${var}    No Operation    ELSE IF   ${cond}    Should Be ",
    )

    _check_should_be_completions(doc, workspace.ws)


def test_keyword_completions_on_template_name(workspace, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """
*** Keyword ***
Example Keyword

*** Test Cases **
Normal test case
    Example keyword    first argument    second argument

Templated test case
    [Template]    Example ke"""
    completion_context = CompletionContext(doc, workspace=workspace.ws)

    completions = keyword_completions.complete(completion_context)
    assert [comp["label"] for comp in completions] == ["Example Keyword (case1)"]


@pytest.mark.parametrize(
    "server_port",
    [
        8270,  # default port
        0,  # let OS decide port
    ],
)
def test_keyword_completions_remote_library(workspace, libspec_manager, remote_library):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case_remote_library", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_remote.robot")
    doc = workspace.put_doc(
        "case_remote.robot",
        doc.source.replace("${PORT}", str(remote_library)) + "\n    a.V",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    completions = keyword_completions.complete(completion_context)
    assert sorted([comp["label"] for comp in completions]) == [
        "Stop Remote Server (a)",
        "Validate String (a)",
        "Verify That Remote Is Running (a)",
    ]


@pytest.mark.parametrize("needs_args", ["LibWithParams", "*", "none"])
def test_keyword_completions_library_with_params_with_space(
    workspace, libspec_manager, needs_args
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    config.update({"robot": {"libraries": {"libdoc": {"needsArgs": [needs_args]}}}})
    libspec_manager.config = config

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_params_on_lib.robot")

    doc.source = """
*** Settings ***
Library    LibWithParams    some_param=foo    WITH NAME    Lib

*** Test Case  ***
My Test
    Lib.Foo"""

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(completion_context)

    if needs_args == "none":
        assert not completions
    else:
        assert len(completions) == 1
        assert sorted([comp["label"] for comp in completions]) == ["Foo Method (Lib)"]


def test_keyword_completions_library_with_params_resolves_var(
    workspace, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    config.update(
        {
            "robot.libraries": {"libdoc": {"needsArgs": ["LibWithParams"]}},
            "robot.variables": {"param_val": "foo"},
        }
    )
    libspec_manager.config = config

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_params_on_lib.robot")

    doc.source = """
*** Settings ***
Library    LibWithParams    some_param=${param_val}    WITH NAME    Lib

*** Test Case  ***
My Test
    Lib.Foo"""

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(completion_context)

    assert len(completions) == 1
    assert sorted([comp["label"] for comp in completions]) == ["Foo Method (Lib)"]


@pytest.mark.parametrize("lib_param", ["bar", "foo"])
def test_code_analysis_same_lib_with_alias_with_params(
    workspace, libspec_manager, cases, lib_param
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.put_doc("case_params_on_lib.robot")
    doc.source = f"""
*** Settings ***
Library   LibWithParams    some_param=foo    WITH NAME   LibFoo
Library   LibWithParams    some_param=bar    WITH NAME   LibBar

*** Test Case ***
My Test
    Lib{lib_param.title()}.{lib_param}"""

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)
    completions = keyword_completions.complete(completion_context)
    assert len(completions) == 1
    assert sorted([comp["label"] for comp in completions]) == [
        f"{lib_param.title()} Method (Lib{lib_param.title()})"
    ]


def apply_completion(doc, completion):
    text_edit = completion["textEdit"]
    doc.apply_text_edits([text_edit])


def test_apply_keyword_with_existing_arguments(workspace):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case2")
    doc = workspace.put_doc(
        "case2.robot",
        """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    My Keyw    $v1    $v2""",
    )

    line, col = doc.get_last_line_col()
    col -= len("    $v1    $v2")

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "My Keyword (case2)",
    ]

    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    My Keyword    $v1    $v2"""
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "basic",
        "already_dotted",
        "with_alias",
        "with_alias_already_dotted",
        "with_resource",
        "dotted_with_resource",
        "builtin",
    ],
)
def test_apply_keyword_with_module_prefix(
    workspace, libspec_manager, scenario, debug_cache_deps
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME,
    )
    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case2", libspec_manager=libspec_manager)
    workspace.put_doc(
        "my/case1.robot",
        """
*** Keywords ***
My Keyword
    No Operation""",
    )

    if scenario == "basic":
        curr_call = "Copy Dict"
        library_or_resource_import = "Library    Collections"
        result = "Collections.Copy Dictionary    ${1:dictionary}"
        label = "Copy Dictionary (Collections)"

    elif scenario == "already_dotted":
        curr_call = "Collections.Copy Dict"
        library_or_resource_import = "Library    Collections"
        result = "Collections.Copy Dictionary    ${1:dictionary}"
        label = "Collections.Copy Dictionary"

    elif scenario == "with_alias":
        curr_call = "Copy Dict"
        library_or_resource_import = "Library    Collections  WITH NAME   Col"
        result = "Col.Copy Dictionary    ${1:dictionary}"
        label = "Copy Dictionary (Col)"

    elif scenario == "with_alias_already_dotted":
        curr_call = "Col.Copy Dict"
        library_or_resource_import = "Library    Collections  WITH NAME   Col"
        result = "Col.Copy Dictionary    ${1:dictionary}"
        label = "Col.Copy Dictionary"

    elif scenario == "with_resource":
        curr_call = "My Keyw"
        library_or_resource_import = "Resource    ./my/case1.robot"
        result = "case1.My Keyword"
        label = "My Keyword (case1)"

    elif scenario == "dotted_with_resource":
        curr_call = "case1.My Keyw"
        library_or_resource_import = "Resource    ./my/case1.robot"
        result = "case1.My Keyword"
        label = "case1.My Keyword"

    elif scenario == "builtin":
        curr_call = "BuiltIn.Log To Cons"
        library_or_resource_import = ""
        result = "BuiltIn.Log To Console    ${1:message}"
        label = "BuiltIn.Log To Console"

    doc = workspace.put_doc(
        "case2.robot",
        f"""*** Settings ***
{library_or_resource_import}

*** Test Cases ***
Test
    {curr_call}""",
    )

    config = RobotConfig()
    config.update({OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME: True})

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config, tracing=True)
    )

    assert len(completions) == 1
    assert completions[0]["label"] == label

    apply_completion(doc, completions[0])

    assert (
        doc.source
        == f"""*** Settings ***
{library_or_resource_import}

*** Test Cases ***
Test
    {result}"""
    )


def test_apply_keyword_arguments_customized(workspace):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR,
    )

    workspace.set_root("case2")
    config = RobotConfig()
    config.update({OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR: "\t"})

    doc = workspace.put_doc(
        "case2.robot",
        """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    My Keyw""",
    )

    line, col = doc.get_last_line_col()

    completions = keyword_completions.complete(
        CompletionContext(
            doc, workspace=workspace.ws, line=line, col=col, config=config
        )
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "My Keyword (case2)",
    ]

    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    My Keyword\t${1:\$v1}\t${2:\$v2}"""
    )


def test_keyword_without_arguments_on_template(workspace):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case2")
    doc = workspace.put_doc(
        "case2.robot",
        """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    [Template]    My Keyw""",
    )

    line, col = doc.get_last_line_col()

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "My Keyword (case2)",
    ]

    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Keywords ***
My Keyword
    [Arguments]    ${v1}    ${v2}
    Log to console    ${v1}${v2}

*** Test Case ***
My Test
    [Template]    My Keyword"""
    )
