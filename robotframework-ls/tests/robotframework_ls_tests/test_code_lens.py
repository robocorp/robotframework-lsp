def test_code_lens_run_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens_runs
    from robotframework_ls.impl.code_lens import code_lens_resolve

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """

*** Test Cases ***
Some Test
    [Documentation]      Docs
    
*** Task ***
Some Task
    [Documentation]      Docs
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens_runs(completion_context)
    check_code_lens_data_regression(data_regression, found)
    for c in found:
        # i.e.: don't change anything here
        assert code_lens_resolve(completion_context, c) == c


def test_code_lens_with_comment(workspace, libspec_manager, data_regression):
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens_runs
    from robotframework_ls.impl.code_lens import code_lens_resolve
    from robotframework_ls.impl.code_lens import code_lens_rf_interactive

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Test Cases ***
# robocop: disable=0505
Foo
    BuiltIn.Log To Console    bar
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens_runs(completion_context)
    found.extend(code_lens_rf_interactive(completion_context))
    check_code_lens_data_regression(data_regression, found)
    new_found = [code_lens_resolve(completion_context, c) for c in found]
    check_code_lens_data_regression(
        data_regression, new_found, basename="test_code_lens_with_comment_after_resolve"
    )


def test_code_lens_scratchpad_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls_tests.fixtures import check_code_lens_data_regression
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens_rf_interactive
    from robotframework_ls.impl.code_lens import code_lens_resolve

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """

*** Settings ***
Library     my_lib.py
Resource    my_resource.robot

*** Test Cases ***
Some Test
    [Documentation]      Docs
    Some Keyword
    
*** Keyword ***
Some Keyword
    Log    Something    console=True
    
*** Variables ***
${foo}      1
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens_rf_interactive(completion_context)
    check_code_lens_data_regression(
        data_regression,
        found,
        basename="test_code_lens_scratchpad_basic_before_resolve",
    )

    new_found = [code_lens_resolve(completion_context, c) for c in found]
    check_code_lens_data_regression(
        data_regression,
        new_found,
        basename="test_code_lens_scratchpad_basic_after_resolve",
    )
