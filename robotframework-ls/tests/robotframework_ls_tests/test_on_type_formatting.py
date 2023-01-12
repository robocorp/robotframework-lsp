def test_on_type_formatting_basic(workspace, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.on_type_formatting import on_type_formatting

    workspace.set_root("case4")
    doc = workspace.put_doc(
        "my.robot",
        """
*** Test Cases ***
Test case 1
    Append to list    foo""",
    )

    line, col = doc.get_last_line_col()

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = on_type_formatting(completion_context, ch="\n")
    assert not result
