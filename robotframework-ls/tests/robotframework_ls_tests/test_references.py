import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version


def check_data_regression(result, data_regression):
    from robocorp_ls_core import uris
    from os.path import basename

    data = {}
    for item in result:
        as_fs_path = uris.to_fs_path(item.pop("uri"))

        name = basename(as_fs_path.replace("\\", "/"))
        if name.endswith(".py"):
            item = "found_in_py_line_col"
        if name in data:
            data[name].append(item)
        else:
            data[name] = [item]

    data_regression.check(sorted(data.items()))


def test_references_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root(
        "case_inner_keywords", libspec_manager=libspec_manager, index_workspace=True
    )
    doc = workspace.get_doc("case_root.robot")

    line = doc.find_line_with_contents("    Should Be Equal     ${arg1}     ${arg2}")
    col = 6
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


def test_references_from_keyword_definition(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.get_doc("case4resource3.robot")

    line = doc.find_line_with_contents("Yet Another Equal Redefined")
    col = 6
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


def test_references_with_name_1(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root(
        "case_with_name", libspec_manager=libspec_manager, index_workspace=True
    )
    doc = workspace.get_doc("case_with_name.robot")

    line = doc.find_line_with_contents("    settodictionary    ${dict}    b=20")
    col = 6
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


def test_references_with_name_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root(
        "case_with_name", libspec_manager=libspec_manager, index_workspace=True
    )
    doc = workspace.get_doc("case_with_name.robot")

    line = doc.find_line_with_contents("    Lib.Set to dictionary    ${dict}    a=10")
    col = 10
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


def test_references_keyword_with_vars(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my.robot")
    doc.source = """
*** Test Cases ***
My Test
    my task 222


*** Keywords ***
My task ${something}
    Log    ${something}
    """

    line = doc.find_line_with_contents("My task ${something}")

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=4
    )
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


def test_references_multiple(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root(
        "case_references", libspec_manager=libspec_manager, index_workspace=True
    )
    doc = workspace.get_doc("case_references.robot")

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = references(completion_context, include_declaration=True)
    assert result

    check_data_regression(result, data_regression)


@pytest.mark.skipif(
    get_robot_major_version() < 4, reason="If only available in RF 4 onwards."
)
def test_references_variables(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Keywords ***
Example 
    ${foo}=    Set Variable    ${None}
    IF    $foo
        Log To Console    foo
    END
    ${bar}=    Set Variable    ${None}
    Log To Console    ${bar}
    """,
    )
    line = doc.find_line_with_contents("    ${foo}=    Set Variable    ${None}")
    col = 7
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    check_data_regression(result, data_regression)


@pytest.mark.skipif(
    get_robot_major_version() < 4, reason="If only available in RF 4 onwards."
)
def test_references_variables_only_local(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Keywords ***
Example1
    ${foo}=    Set Variable    ${None}
    Log To Console    ${foo}
    
Example2 
    ${foo}=    Set Variable    ${None}
    Log To Console    ${foo}
    """,
    )
    line = doc.find_line_with_contents("    ${foo}=    Set Variable    ${None}")
    col = 7
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    check_data_regression(result, data_regression)


@pytest.mark.skipif(
    get_robot_major_version() < 4, reason="If only available in RF 4 onwards."
)
def test_references_variables_in_expr(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Test Cases ***
Demo
    ${var1}    Set Variable    2
    IF    ${{$var1 != "1"}}
        Fail
    END
    """,
    )
    line = doc.find_line_with_contents('    IF    ${{$var1 != "1"}}')
    col = len("    IF    ${{$v")

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    check_data_regression(result, data_regression)


def test_references_variables_previous_var(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Keywords ***
Keyword
        [Arguments]     ${foo}    ${bar}=${foo}
        Log     ${foo}
    """,
    )
    line = doc.find_line_with_contents("        Log     ${foo}")
    col = len("        Log     ${f")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    check_data_regression(result, data_regression)


def test_references_variables_named_arguments_different_doc(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "casedef.robot",
        """
*** Keywords ***
My Keyword
        [Arguments]     ${Foo}
        Log     ${fOo}
    """,
    )

    workspace.put_doc(
        "caseref.robot",
        """
*** Settings ***
Resource    casedef.robot

*** Test Case ***
My Test
        My Keyword    foO=22
    """,
    )

    line = doc.find_line_with_contents("        Log     ${fOo}")
    col = len("        Log     ${f")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    assert len(result) == 3
    check_data_regression(result, data_regression)


def test_references_variables_named_arguments_same_doc(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "casedef.robot",
        """
*** Keywords ***
My Keyword
        [Arguments]     ${Foo}
        Log     ${fOo}

*** Test Case ***
My Test
        My Keyword    foO=22
    """,
    )

    line = doc.find_line_with_contents("        Log     ${fOo}")
    col = len("        Log     ${f")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    assert len(result) == 3
    check_data_regression(result, data_regression)


def test_references_var_in_exp(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Test Cases ***
Check
    ${aa}=    Evaluate    2
    Log to console    ${aa + 1}
    """,
    )
    line = doc.find_line_with_contents("    Log to console    ${aa + 1}")
    col = len("    Log to console    ${a")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = references(completion_context, include_declaration=True)
    assert result
    check_data_regression(result, data_regression)


def test_references_var_with_constructed_vars(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    [Setup]    Initialize Variables
    Log    ${SOME_VARIABLE_0}
    Log    ${SOME_VARIABLE_1}
    Log    ${SOME_VARIABLE_2}

*** Keywords ***
Initialize Variables
    FOR    ${index}    IN RANGE    3
        Set Test Variable    ${SOME_VARIABLE_${index}}    Value ${index}
    END
"""

    line, col = doc.get_last_line_col_with_contents("    Log    ${SOME_VARIABLE_0}")
    col -= len("E_0}")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    result = references(completion_context, include_declaration=True)
    check_data_regression(result, data_regression)


def test_references_global_vars(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.references import references

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    Set Global Variable    ${someglobalvar}
    Log    ${SOME_GLOBAL_VAR}
"""

    doc2 = workspace.put_doc("case2a.robot")
    doc2.source = """
*** Keywords ***
Some Keyword
    Set Global Variable    ${someglobalvar}
    Set Global Variable    ${someglobalvar}
"""

    line, col = doc.get_last_line_col_with_contents("    Log    ${SOME_GLOBAL_VAR}")
    col -= 2
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    result = references(completion_context, include_declaration=True)
    check_data_regression(result, data_regression)
