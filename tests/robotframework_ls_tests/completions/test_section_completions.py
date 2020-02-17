def test_section_completions(data_regression):
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.workspace import Document

    doc = Document("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="header_completions_all")

    doc = Document("unused", source="""**settin""")
    completions = section_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="header_completions_filter_settings")
