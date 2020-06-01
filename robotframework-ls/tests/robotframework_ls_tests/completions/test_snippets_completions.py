def test_snippets_completions(data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import snippets_completions

    doc = RobotDocument("unused", source="""for""")
    completions = snippets_completions.complete(CompletionContext(doc))

    data_regression.check(completions)
