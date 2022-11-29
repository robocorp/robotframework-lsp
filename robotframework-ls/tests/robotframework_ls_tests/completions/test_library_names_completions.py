def apply_completion(doc, completion, expect_additional_text_edits=False):
    text_edit = completion["textEdit"]
    additional_text_edits = completion.get("additionalTextEdits")
    if expect_additional_text_edits:
        assert additional_text_edits
    else:
        assert not additional_text_edits
    doc.apply_text_edits([text_edit])
    if additional_text_edits:
        doc.apply_text_edits(additional_text_edits)


def test_library_names_completions_basic(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library           Collections

*** Keywords ***
My Keyword
    Col"""

    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    data_regression.check(completions)

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library           Collections

*** Keywords ***
My Keyword
    Collections"""
    )


def test_library_names_completions_alias(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library           Collections    WITH NAME     Alpha

*** Keywords ***
My Keyword
    al"""

    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    data_regression.check(completions)

    assert len(completions) == 1
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library           Collections    WITH NAME     Alpha

*** Keywords ***
My Keyword
    Alpha"""
    )


def test_library_names_completions_only_until_dot(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library           Collections

*** Keywords ***
My Keyword
    Col.AddToList"""

    line, col = doc.get_last_line_col()
    col -= len(".AddToList")
    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
    )

    assert len(completions) == 1
    data_regression.check(completions)
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library           Collections

*** Keywords ***
My Keyword
    Collections.AddToList"""
    )


def test_library_names_completions_only_basename(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library           ../foo/Mylibrary.py

*** Keywords ***
My Keyword
    myl"""

    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    assert len(completions) == 1
    data_regression.check(completions)
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library           ../foo/Mylibrary.py

*** Keywords ***
My Keyword
    Mylibrary"""
    )


def test_library_names_completions_only_basename_with_var(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library           ../foo${/}Mylibrary.py

*** Keywords ***
My Keyword
    myl"""

    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    assert len(completions) == 1
    data_regression.check(completions)
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Library           ../foo${/}Mylibrary.py

*** Keywords ***
My Keyword
    Mylibrary"""
    )


def test_resource_names_completions(
    data_regression, workspace, cases, libspec_manager, workspace_dir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import library_names_completions

    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Resource           ../foo${/}myrobot.robot

*** Keywords ***
My Keyword
    my"""

    completions = library_names_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )

    assert len(completions) == 1
    # data_regression.check(completions)
    apply_completion(doc, completions[0])

    assert (
        doc.source
        == """*** Settings ***
Resource           ../foo${/}myrobot.robot

*** Keywords ***
My Keyword
    myrobot"""
    )
