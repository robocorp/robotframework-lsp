import pytest


def test_formatting_basic(data_regression):
    try:
        from robot.tidy import Tidy
    except ImportError:
        pytest.skip("robot.tidy is no longer available.")

    from robotframework_ls.impl.formatting import (
        robot_source_format,
        create_text_edit_from_diff,
    )
    from robocorp_ls_core.workspace import Document

    contents = """
***Settings***
[Documentation]Some doc

***Test Case***
Check
    Call  1  2"""
    new_contents = robot_source_format(contents)
    assert "*** Settings ***" in new_contents

    text_edits = create_text_edit_from_diff(contents, new_contents)

    doc = Document("", contents)
    doc.apply_text_edits(text_edits)
    data_regression.check(doc.source, basename="test_formatting_basic_formatted_doc")
    data_regression.check(
        [x.to_dict() for x in text_edits], basename="test_formatting_basic_text_edits"
    )


def test_robotframework_tidy_formatting():
    from robotframework_ls_tests.fixtures import initialize_robotframework_server_api
    from robocorp_ls_core.jsonrpc.monitor import Monitor
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY,
    )
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_CODE_FORMATTER

    api = initialize_robotframework_server_api()
    api.m_workspace__did_change_configuration(
        settings={OPTION_ROBOT_CODE_FORMATTER: OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY}
    )
    uri = "untitled"

    api.m_text_document__did_open(textDocument={"uri": uri})

    # This should be formatted as expected already!
    text = """*** Test Cases ***
Demo2
    No operation


*** Keywords ***
Some keyword
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )

    api.m_text_document__did_change(
        textDocument={"uri": uri},
        contentChanges=[{"text": text}],
    )

    monitor = Monitor()
    for _i in range(3):
        changes = api._threaded_code_format({"uri": uri}, None, monitor)
        assert not changes
