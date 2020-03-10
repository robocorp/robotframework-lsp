def test_section_completions(data_regression, workspace):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1")
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    ve"

    completions = keyword_completions.complete(CompletionContext(doc))


#   WORK IN PROGRES...
#     doc = Document("unused", source="""**settin""")
#     completions = section_completions.complete(CompletionContext(doc))
#     data_regression.check(completions, basename="header_completions_filter_settings")
