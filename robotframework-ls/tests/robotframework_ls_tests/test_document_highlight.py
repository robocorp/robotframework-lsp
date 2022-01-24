def test_document_highlight_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Collections.Append to list    foo
    Append to list    foo
    append_to_list    foo""",
    )

    line = doc.find_line_with_contents("append_to_list")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)


def test_document_highlight_with_keyword(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Keywords ***
My Keyword
    Log to console    Something

*** Test Cases ***
Test case 1
    My Keyword
    Mykeyword""",
    )

    line = doc.find_line_with_contents("My Keyword")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)

    # The result must be the same from definition or usage selection
    line = doc.find_line_with_contents("Mykeyword")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)


def test_document_highlight_generic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Keywords ***
My Keyword
    Log to console    Something

*** Test Cases ***
Test case 1
    Log    Something    IgnoreSomethingIgnore""",
    )

    line_contents = "    Log to console    Something"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 1
    )
    result = doc_highlight(completion_context)
    assert result
    assert len(result) == 2
    data_regression.check(result)
