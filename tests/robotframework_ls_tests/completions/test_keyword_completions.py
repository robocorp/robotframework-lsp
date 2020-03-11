def test_keyword_completions(data_regression, workspace):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.libspec_manager import LibspecManager

    workspace.set_root("case1", libspec_manager=LibspecManager())
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    ve"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_1")
