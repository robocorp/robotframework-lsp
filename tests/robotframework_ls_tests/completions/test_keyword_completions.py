import pytest


def test_keyword_completions_builtin(workspace, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    should be"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "Length Should Be",
        "Should Be Empty",
        "Should Be Equal",
        "Should Be Equal As Integers",
        "Should Be Equal As Numbers",
        "Should Be Equal As Strings",
        "Should Be True",
    ]


@pytest.mark.parametrize(
    "library_import", ["case1_library", "case1_library.py", "__FULL_PATH__"]
)
def test_keyword_completions_user_library(
    data_regression, workspace, tmpdir, cases, libspec_manager, library_import
):
    import os.path
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robotframework_ls import uris

    workspace_dir = str(tmpdir.join("workspace"))
    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")

    if library_import == "__FULL_PATH__":
        case1_robot_path = uris.to_fs_path(doc.uri)
        case1_py_path = os.path.join(
            os.path.dirname(case1_robot_path), "case1_library.py"
        )
        library_import = case1_py_path

    doc.source = doc.source.replace("case1_library", library_import)
    doc.source = doc.source + "\n    verify"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_1")

    # Now, let's put a .libspec file in the workspace and check whether
    # it has priority over the auto-generated spec file.
    with open(os.path.join(workspace_dir, "new_spec.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.synchronize_workspace_folders()

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_2_new")


def test_keyword_completions_user_in_robot_file(
    data_regression, workspace, cases, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root(cases.get_path("case2"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc.source = doc.source + "\n    my equ"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(
        completions, basename="keyword_completions_user_in_robot_file"
    )


def test_keyword_completions_from_resource_files(
    data_regression, workspace, tmpdir, cases, libspec_manager
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.config.config import Config
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

    config = Config(root_uri="", init_opts={}, process_id=-1, capabilities={})
    config.update({"robot": {"variables": {"ext_folder": cases.get_path("ext")}}})
    assert config.get_setting(OPTION_ROBOT_VARIABLES, dict, {}) == {
        "ext_folder": cases.get_path("ext")
    }

    workspace.set_root(cases.get_path("case3"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case3.robot")
    doc.source = doc.source + "\n    equal redef"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config)
    )
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
    doc.source = doc.source + "\n    equal redef"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    data_regression.check(
        completions, basename="keyword_completions_from_recursively_resource_files"
    )


def test_keyword_completions_builtin_duplicated(workspace, cases, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root(cases.get_path("case4"), libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = doc.source + "\n    should be equal"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "should be equal"
    ]

    assert len(found) == 1


def test_keyword_completions_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc.source = doc.source + "\n    [Teardown]    my_Equal red"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "my equal redefined"
    ]

    assert len(found) == 1


def test_keyword_completions_settings_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc.source = doc.source + "\n*** Keywords ***\nTeardown    my_Equal red"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion["label"]
        for completion in completions
        if completion["label"].lower() == "my equal redefined"
    ]

    assert len(found) == 1


def test_keyword_completions_bdd_prefix(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc.source = doc.source + "\n*** Keywords ***\nTeardown    WHEN my_Equal red"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    found = [
        completion
        for completion in completions
        if completion["label"].lower() == "my equal redefined"
    ]
    data_regression.check(found)


def test_keyword_completions_template(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import keyword_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
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
        if completion["label"].lower() == "my equal redefined"
    ]

    assert len(found) == 1


def test_keyword_completions_library_prefix(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")

    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3."""

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

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

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    data_regression.check(
        completions, basename="test_keyword_completions_library_prefix_2"
    )

    doc.source = """*** Settings ***
Library    Collections

*** Test Cases ***
Test
    Collections.Append To Lis"""

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert [completion["label"] for completion in completions] == ["Append To List"]
