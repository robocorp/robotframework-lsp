import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version


def test_hover_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Log""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert "Log" in contents["value"]
    assert contents["kind"] == "markdown"


def test_hover_argument(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Log    Something""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert contents["value"].startswith("Parameter: *`message`* in Keyword Call.")


def test_hover_argument_in_run_keyword(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Run Keyword    Log    Something""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert contents["value"].startswith("Parameter: *`message`* in Keyword Call.")


def test_hover_basic_in_keyword_argument(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Run Keyword If    ${var}    Log""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert "Log" in contents["value"]
    assert contents["kind"] == "markdown"


def test_hover_suite_setup(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Settings ***
Suite Setup    Run Keyword    Log""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert "Log" in contents["value"]
    assert contents["kind"] == "markdown"


def test_hover_in_run_keywords(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Run Keywords    Log    22    AND    Log to Console""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result

    contents = result["contents"]
    assert "Log To Console" in contents["value"]
    assert contents["kind"] == "markdown"


def test_hover_doc_format(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keyword ***
Some Keyword
    [Documentation]    Some *table* in docs
    ...  | =A= |  =B=  | = C =  |
    ...  | _1_ | Hello | world! |
    ...  | _2_ | Hi    |        |   
    
*** Test Case ***
Some test
    Some Keyword""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = hover(completion_context)
    assert result
    data_regression.check(result["contents"])


def _convert_to_compare(doc_contents, hover_contents, range_found):
    value = "\n".join(hover_contents["value"].split("\n")[:3])
    assert hover_contents["kind"] == "markdown"
    return {
        "doc": doc_contents,
        "hover": value,
    }


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards")
def test_hover_full(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.hover import hover

    workspace.set_root("ext", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_hover.robot", accept_from_file=True)

    all_found = []
    last_result = None
    for offset in range(len(doc)):
        line, col = doc.offset_to_line_col(offset)
        completion_context = CompletionContext(
            doc, workspace=workspace.ws, line=line, col=col
        )

        result = hover(completion_context)
        if result:
            found = (result["contents"], result["range"])
            range_start_found = result["range"]["start"]
            range_end_found = result["range"]["end"]
            if last_result != found:
                doc_contents = doc.get_range(
                    range_start_found["line"],
                    range_start_found["character"],
                    range_end_found["line"],
                    range_end_found["character"],
                )

                full_line = doc.get_line(range_start_found["line"])
                last_result = found
                all_found.append(
                    _convert_to_compare(
                        doc_contents + " (line: " + full_line + ")",
                        result["contents"],
                        result["range"],
                    )
                )

    data_regression.check(all_found)
