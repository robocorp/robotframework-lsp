def test_formatting_basic(data_regression):
    from robotframework_ls.impl.formatting import (
        robot_source_format,
        create_text_edit_from_diff,
    )
    from robocorp_ls_core.workspace import Document

    contents = u"""
***Settings***
[Documentation]Some doc

***Test Case***
Check
    Call  1  2"""
    new_contents = robot_source_format(contents)
    assert u"*** Settings ***" in new_contents

    text_edits = create_text_edit_from_diff(contents, new_contents)

    doc = Document("", contents)
    doc.apply_text_edits(text_edits)
    data_regression.check(doc.source, basename="test_formatting_basic_formatted_doc")
    data_regression.check(
        [x.to_dict() for x in text_edits], basename="test_formatting_basic_text_edits"
    )
