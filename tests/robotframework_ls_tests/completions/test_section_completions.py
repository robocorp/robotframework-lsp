def test_section_completions(data_regression):
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.workspace import Document

    doc = Document("unused", source="""**""")
    completion_context = CompletionContext(doc, 0, 2)
    completions = section_completions.complete(completion_context)
    data_regression.check(completions, basename="header_completions_all")

    doc = Document("unused", source="""**settin""")
    completion_context = CompletionContext(doc, 0, len(doc) - 1)
    completions = section_completions.complete(completion_context)
    data_regression.check(completions, basename="header_completions_filter_settings")
