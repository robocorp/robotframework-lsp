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


def test_section_name_settings_completions(data_regression):
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.workspace import Document

    doc = Document(
        "unused",
        source="""
*** Settings ***

""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_names")

    doc = Document(
        "unused",
        source="""
*** Settings ***

Docum""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_docum_names")


def test_section_name_keywords_completions(data_regression):
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.workspace import Document

    doc = Document(
        "unused",
        source="""
*** keywords ***

""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_no_names")

    doc = Document(
        "unused",
        source="""
*** keywords ***
[""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_names")

    doc = Document(
        "unused",
        source="""
*** keywords ***
[Docum""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_docum_names")

    doc = Document(
        "unused",
        source="""
*** keywords ***
[Docum]""",
    )
    line, col = doc.get_last_line_col()
    completions = section_name_completions.complete(
        CompletionContext(doc, line=line, col=col - 1)
    )
    data_regression.check(completions, basename="keywords_docum_names2")
