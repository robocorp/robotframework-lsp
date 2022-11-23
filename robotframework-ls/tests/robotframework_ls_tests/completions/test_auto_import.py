import pytest
from typing import Dict, List


def apply_completion(doc, completion, expect_additional_text_edits=True):
    text_edit = completion["textEdit"]
    additional_text_edits = completion["additionalTextEdits"]
    if expect_additional_text_edits:
        assert additional_text_edits
    else:
        assert not additional_text_edits
    doc.apply_text_edits([text_edit])
    if additional_text_edits:
        doc.apply_text_edits(additional_text_edits)


def test_completion_with_auto_import_basic_stdlib(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws), {}
    )

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """
*** Settings ***
Library    case1_library
Library    Collections

*** Test Cases ***
User can call library
    Copy Dictionary"""
    )


def test_completion_with_auto_import_disabled(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ENABLE,
    )

    cases.copy_to("case1", workspace_dir)
    config = RobotConfig()
    config.update({OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ENABLE: False})

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config), {}
    )

    assert len(completions) == 0


def test_completion_with_auto_import_dont_add_import(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ADD_IMPORT,
    )

    cases.copy_to("case1", workspace_dir)
    config = RobotConfig()
    config.update({OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ADD_IMPORT: False})

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config), {}
    )

    assert len(completions) == 1
    apply_completion(doc, completions[0], expect_additional_text_edits=False)

    assert (
        doc.source
        == """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Dictionary"""
    )


def test_completion_with_auto_import_dont_prefix_library(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME,
    )

    cases.copy_to("case1", workspace_dir)
    config = RobotConfig()
    config.update({OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME: True})

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config), {}
    )

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """
*** Settings ***
Library    case1_library
Library    Collections

*** Test Cases ***
User can call library
    Collections.Copy Dictionary"""
    )


def test_completion_with_auto_import_keyword_format(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT,
    )

    cases.copy_to("case1", workspace_dir)

    config = RobotConfig()
    # Check that although the options are presented with case, the comparison
    # internally is case-insensitive.
    config.update({OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT: "AlL lowEr"})

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, config=config), {}
    )

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """
*** Settings ***
Library    case1_library
Library    Collections

*** Test Cases ***
User can call library
    copy dictionary"""
    )


def test_completion_with_auto_import_import_not_duplicated_case1_library(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case1.robot",
        """
*** Settings ***
Library    case1_library

*** Test Cases ***
User can call library
    Verify another m""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    # Needed to pre-generate the information
    workspace.ws.libspec_manager.get_library_doc_or_error(
        libname="case1_library",
        create=True,
        completion_context=completion_context,
    )

    completions = auto_import_completions.complete(completion_context, {})

    assert len(completions) == 0


@pytest.fixture
def setup_case2_doc(workspace, cases, libspec_manager, workspace_dir):
    from robocorp_ls_core.lsp import TextDocumentItem
    import os.path
    from robocorp_ls_core import uris

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)

    uri = uris.from_fs_path(os.path.join(workspace_dir, "case2.robot"))
    workspace.ws.put_document(
        TextDocumentItem(
            uri,
            text="""
*** Test Cases ***
User can call library
    Verify another m""",
        )
    )
    doc = workspace.ws.get_document(uri, accept_from_file=False)
    return doc


@pytest.fixture
def setup_case2_in_dir_doc(workspace, cases, libspec_manager, workspace_dir):
    from robocorp_ls_core.lsp import TextDocumentItem
    import os.path
    from robocorp_ls_core import uris

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(
        workspace_dir, libspec_manager=libspec_manager, index_workspace=True
    )

    uri = uris.from_fs_path(os.path.join(workspace_dir, "in_dir", "case2.robot"))
    doc = workspace.ws.put_document(
        TextDocumentItem(
            uri,
            text="""
*** Test Cases ***
User can call library
    Verify another m""",
        )
    )
    return doc


def test_completion_with_auto_import_case1_library_imported_1(
    workspace, setup_case2_doc
):
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    doc = setup_case2_doc
    completion_context = CompletionContext(doc, workspace=workspace.ws)
    # Needed to pre-generate the information
    workspace.ws.libspec_manager.get_library_doc_or_error(
        libname="case1_library",
        create=True,
        completion_context=completion_context,
    )

    # Get completions from the user library adding the *** Settings ***
    completions = auto_import_completions.complete(completion_context, {})

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library    case1_library.py

*** Test Cases ***
User can call library
    Verify Another Model"""
    )


def test_completion_with_auto_import_case1_library_imported_2(
    workspace, setup_case2_doc
):
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    doc = setup_case2_doc
    # Get completions from the user library adding the existing *** Settings ***
    doc.source = """*** Settings ***

*** Test Cases ***
User can call library
    Verify another m"""
    completion_context = CompletionContext(doc, workspace=workspace.ws)

    # Needed to pre-generate the information
    libdoc_or_error = workspace.ws.libspec_manager.get_library_doc_or_error(
        libname="case1_library",
        create=True,
        completion_context=CompletionContext(workspace.get_doc("case1.robot")),
    )
    assert not libdoc_or_error.error

    completions = auto_import_completions.complete(completion_context, {})

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library    case1_library.py

*** Test Cases ***
User can call library
    Verify Another Model"""
    )


def test_completion_with_auto_import_case1_library_imported_3(
    workspace, setup_case2_in_dir_doc
):
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    doc = setup_case2_in_dir_doc

    # Get completions from the user library adding the existing *** Settings ***
    doc.source = """*** Settings ***

*** Test Cases ***
User can call library
    Verify another m"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    # Needed to pre-generate the information
    libdoc_or_error = workspace.ws.libspec_manager.get_library_doc_or_error(
        libname="case1_library",
        create=True,
        completion_context=CompletionContext(workspace.get_doc("case1.robot")),
    )
    assert not libdoc_or_error.error

    completions = auto_import_completions.complete(completion_context, {})

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library    ../case1_library.py

*** Test Cases ***
User can call library
    Verify Another Model"""
    )


def test_completion_with_auto_import_import_not_duplicated_stdlib(
    workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Settings ***
Library    case1_library.py
Library    Collections

*** Test Cases ***
User can call library
    Copy Diction"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws), {}
    )

    # As the Collections library is already there, don't show that completion here
    # (it's already managed in other completions).
    assert len(completions) == 0


def test_completion_with_auto_import_resource_import(workspace, setup_case2_in_dir_doc):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robocorp_ls_core.basic import wait_for_expected_func_return

    doc = workspace.put_doc(
        "case1.robot",
        """
*** Keywords ***
KeywordInCase1
    In Lib 2
""",
    )

    doc2 = setup_case2_in_dir_doc
    doc2.source = """
*** Test Cases ***
User can call library
    KeywordInCa"""

    wait_for_expected_func_return(
        lambda: len(
            auto_import_completions.complete(
                CompletionContext(doc2, workspace=workspace.ws), {}
            )
        ),
        1,
    )
    completions = auto_import_completions.complete(
        CompletionContext(doc2, workspace=workspace.ws), {}
    )

    assert workspace.get_doc("case1.robot") is doc

    assert (
        len(completions) == 1
    ), f"No completions found. Symbols cache: {workspace.get_doc('case1.robot').symbols_cache.get_json_list()}"
    apply_completion(doc2, completions[0])

    assert (
        doc2.source
        == """*** Settings ***
Resource    ../case1.robot

*** Test Cases ***
User can call library
    KeywordInCase1"""
    )


def test_completion_with_auto_import_duplicated(workspace, setup_case2_in_dir_doc):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.impl.protocols import IKeywordFound
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robocorp_ls_core.lsp import TextDocumentItem

    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Keywords ***
KeywordInCase1
    In Lib 2
"""

    # Just create a dummy entry for KeywordInCase1.
    doc_foobar = workspace.ws.put_document(
        TextDocumentItem(
            "foobar",
            text="""
*** Keywords ***
KeywordInCase1
    In Lib 2
""",
        )
    )

    keyword_name_to_keyword_found: Dict[
        str, List[IKeywordFound]
    ] = collect_keyword_name_to_keyword_found(
        CompletionContext(doc_foobar, workspace=workspace.ws)
    )

    doc2 = setup_case2_in_dir_doc
    doc2.source = """
*** Test Cases ***
User can call library
    KeywordInCa"""

    completions = auto_import_completions.complete(
        CompletionContext(doc2, workspace=workspace.ws), keyword_name_to_keyword_found
    )

    assert len(completions) == 0

    # The check done is now only by the keyword name, don't try to resolve if
    # it's a different keyword because it's defined in another file.
    #     assert len(completions) == 1
    #     apply_completion(doc2, completions[0])
    #
    #     assert (
    #         doc2.source
    #         == """*** Settings ***
    # Resource    ../case1.robot
    #
    # *** Test Cases ***
    # User can call library
    #     case1.KeywordInCase1"""
    #     )


def test_completion_with_auto_handle_unparseable_error(
    workspace, setup_case2_in_dir_doc, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    import os.path
    from robocorp_ls_core.basic import wait_for_condition
    import robot

    if robot.get_version().startswith("3."):
        pytest.skip("Flaky on RF 3")

    doc = workspace.put_doc("case1.robot")
    doc.source = """/invalid/file/here ustehous usneothu snteuha usoentuho"""

    os.makedirs(os.path.join(workspace_dir, "in_dir"), exist_ok=True)
    with open(os.path.join(workspace_dir, "in_dir", "case3.robot"), "w") as stream:
        stream.write(
            """
*** Keywords ***
KeywordInCase1
    In Lib 2"""
        )

    doc2 = setup_case2_in_dir_doc
    doc2.source = """
*** Test Cases ***
User can call library
    KeywordInCa"""

    # i.e.: make sure that our in-memory folders are in sync.
    wait_for_condition(
        lambda: len(
            auto_import_completions.complete(
                CompletionContext(doc2, workspace=workspace.ws), {}
            )
        )
        == 1
    )

    completions = auto_import_completions.complete(
        CompletionContext(doc2, workspace=workspace.ws), {}
    )

    assert len(completions) == 1

    apply_completion(doc2, completions[0])

    assert (
        doc2.source
        == """*** Settings ***
Resource    case3.robot

*** Test Cases ***
User can call library
    KeywordInCase1"""
    )


def test_completion_not_duplicated(workspace, cases, libspec_manager, workspace_dir):
    from robocorp_ls_core.lsp import TextDocumentItem
    import os.path
    from robocorp_ls_core import uris
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robotframework_ls.impl.protocols import IKeywordFound

    cases.copy_to("case_inner_keywords", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    config = RobotConfig()
    config.update({"robot.pythonpath": [workspace_dir]})
    libspec_manager.config = config

    uri = uris.from_fs_path(os.path.join(workspace_dir, "inner", "case_inner.robot"))
    workspace.ws.put_document(
        TextDocumentItem(
            uri,
            text="""*** Settings ***
Resource    case_root.robot

*** Keywords ***
Check with keyword at inner
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Test Cases ***
Testing Completion Here
    Check with ke""",
        )
    )
    doc = workspace.ws.get_document(uri, accept_from_file=False)

    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions

    workspace.ws.wait_for_check_done(5)
    context = CompletionContext(doc, workspace=workspace.ws, config=config)

    keyword_name_to_keyword_found: Dict[
        str, List[IKeywordFound]
    ] = collect_keyword_name_to_keyword_found(context)

    completions = auto_import_completions.complete(
        context, keyword_name_to_keyword_found
    )

    # I.e.: all the related symbols are already imported and will be shown
    # in the regular completion.
    assert len(completions) == 0


def test_no_reserved_keywords(workspace, setup_case2_in_dir_doc):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions

    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Keywords ***
KeywordInCase1
    Else i"""

    completions = auto_import_completions.complete(
        CompletionContext(doc, workspace=workspace.ws), {}
    )
    for completion in completions:
        assert completion["label"] != "Else If (Reserved)"


def test_collect_from_pre_specified_pythonpath(
    workspace, cases, libspec_manager, monkeypatch
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.robot_config import RobotConfig
    from robocorp_ls_core.basic import wait_for_expected_func_return

    monkeypatch.setenv("ROBOTFRAMEWORK_LS_PRE_GENERATE_PYTHONPATH_LIBS", "1")

    workspace.set_root("case1", libspec_manager=libspec_manager)

    pythonpath = [cases.get_path("case1"), cases.get_path("case_search_pythonpath")]
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": pythonpath,
                "libraries": {
                    "libdoc": {"preGenerate": ["libraries.lib_in_pythonpath"]}
                },
            }
        }
    )
    libspec_manager.pre_generate_libspecs = True
    libspec_manager.config = config
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Keywords ***
KeywordInCase1
    Find in lib"""

    def check():
        completions = auto_import_completions.complete(
            CompletionContext(doc, workspace=workspace.ws), {}
        )
        return [c["label"] for c in completions]

    # The libspec generation will run in a thread at startup, thus, we need
    # to wait for this condition to be reached.
    wait_for_expected_func_return(
        check, ["Find In Library (libraries.lib_in_pythonpath)*"]
    )
