def test_section_completions(data_regression):
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.config.config import Config

    config = Config(root_uri="", init_opts={}, process_id=-1, capabilities={})
    config.update({"robot": {"completions": {"section_headers": {"form": "both"}}}})

    doc = RobotDocument("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    data_regression.check(completions, basename="header_completions_all")

    doc = RobotDocument("unused", source="""**settin""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    data_regression.check(completions, basename="header_completions_filter_settings")

    config.update({})
    doc = RobotDocument("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    data_regression.check(completions, basename="header_completions_all_plural")


def test_section_name_settings_completions(data_regression):
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="""
*** Settings ***

""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_names")

    doc = RobotDocument(
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
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="""
*** keywords ***

""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_no_names")

    doc = RobotDocument(
        "unused",
        source="""
*** keywords ***
[""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_names")

    doc = RobotDocument(
        "unused",
        source="""
*** keywords ***
[Docum""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="keywords_docum_names")

    doc = RobotDocument(
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
