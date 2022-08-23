import pytest


def test_section_completions(data_regression):
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    supports_language = robot_version_supports_language()

    config = RobotConfig()
    config.update({"robot": {"completions": {"section_headers": {"form": "both"}}}})

    doc = RobotDocument("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    if supports_language:
        # RF 5.1 onwards only provides plural support.
        data_regression.check(completions, basename="header_completions_all_plural")
    else:
        data_regression.check(completions, basename="header_completions_all")

    doc = RobotDocument("unused", source="""**settin""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    if supports_language:
        # RF 5.1 onwards only provides plural support.
        data_regression.check(
            completions, basename="header_completions_filter_settings_plural"
        )
    else:
        data_regression.check(
            completions, basename="header_completions_filter_settings"
        )

    config.update({})
    doc = RobotDocument("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc, config=config))
    data_regression.check(completions, basename="header_completions_all_plural")


def test_section_completions_inline0():
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="*** Test Case ***",
    )
    last_line = 0
    col = len("*** Test Ca")
    completions = section_completions.complete(
        CompletionContext(doc, line=last_line, col=col)
    )
    for c in completions:
        if c["label"] == "*** Test Cases ***":
            doc.apply_text_edits([c["textEdit"]])
            break
    else:
        raise AssertionError("Did not find test case.")

    assert doc.source == "*** Test Cases ***"


def test_section_completions_inline1():
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="*** Test Case ***  # Comment",
    )
    last_line = 0
    col = len("*** Test Ca")
    completions = section_completions.complete(
        CompletionContext(doc, line=last_line, col=col)
    )
    for c in completions:
        if c["label"] == "*** Test Cases ***":
            doc.apply_text_edits([c["textEdit"]])
            break
    else:
        raise AssertionError("Did not find test case.")

    assert doc.source == "*** Test Cases ***  # Comment"


def test_section_completions_inline2():
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="*** Test Ca",
    )
    last_line = 0
    col = len("*** Test Ca")
    completions = section_completions.complete(
        CompletionContext(doc, line=last_line, col=col)
    )
    for c in completions:
        if c["label"] == "*** Test Cases ***":
            doc.apply_text_edits([c["textEdit"]])
            break
    else:
        raise AssertionError("Did not find test case.")

    assert doc.source == "*** Test Cases ***"


def test_section_completions_inline3():
    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="*** Test Ca * foobar",
    )
    last_line = 0
    col = len("*** Test Ca")
    completions = section_completions.complete(
        CompletionContext(doc, line=last_line, col=col)
    )
    for c in completions:
        if c["label"] == "*** Test Cases ***":
            doc.apply_text_edits([c["textEdit"]])
            break
    else:
        raise AssertionError("Did not find test case.")

    assert doc.source == "*** Test Cases *** foobar"


def test_section_completions_localization(data_regression):
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    if not robot_version_supports_language():
        raise pytest.skip("Test requires language support.")

    from robotframework_ls.impl import section_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.robot_localization import set_global_localization_info
    from robotframework_ls.impl.robot_localization import LocalizationInfo

    set_global_localization_info(LocalizationInfo(["pt-br"]))

    doc = RobotDocument("unused", source="""**""")
    completions = section_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="header_completions_all_pt_br")


def test_section_name_settings_completions_localization(data_regression):
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    if not robot_version_supports_language():
        raise pytest.skip("Test requires language support.")

    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="""
language: pt-br
*** Configurações ***

""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_names_pt_br")

    doc = RobotDocument(
        "unused",
        source="""
language: pt-br
*** Configurações ***

Docum""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_docum_names_pt_br")


def test_section_name_settings_completions(data_regression):
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.robot_version import get_robot_major_minor_version

    doc = RobotDocument(
        "unused",
        source="""
*** Settings ***

""",
    )
    postfix = "51"
    if get_robot_major_minor_version() < (5, 1):
        postfix = "pre_51"
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_names_" + postfix)

    doc = RobotDocument(
        "unused",
        source="""
*** Settings ***

Docum""",
    )
    completions = section_name_completions.complete(CompletionContext(doc))
    data_regression.check(completions, basename="settings_docum_names")


def test_section_name_settings_completions_inline(data_regression):
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused",
        source="""

*** Test Cases ***
Test 
    No Operation
    []No Operation""",
    )
    last_line = doc.get_line_count() - 1
    col = len("    [")
    completions = section_name_completions.complete(
        CompletionContext(doc, line=last_line, col=col)
    )
    for c in completions:
        if c["label"] == "[Teardown]":
            doc.apply_text_edits([c["textEdit"]])
            break
    else:
        raise AssertionError("Did not find teardown.")

    assert (
        doc.source
        == """

*** Test Cases ***
Test 
    No Operation
    [Teardown]No Operation"""
    )


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
