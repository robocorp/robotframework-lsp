def test_document_highlight_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Collections.Append to list    foo
    Append to list    foo
    append_to_list    foo""",
    )

    line = doc.find_line_with_contents("append_to_list")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)


def test_document_highlight_with_keyword(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Keywords ***
My Keyword
    Log to console    Something

*** Test Cases ***
Test case 1
    My Keyword
    Mykeyword""",
    )

    line = doc.find_line_with_contents("My Keyword")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)

    # The result must be the same from definition or usage selection
    line = doc.find_line_with_contents("Mykeyword")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=6
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(result)


def test_document_highlight_keyword_namespace(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Append to list
    Collections.Append to list""",
    )

    line_contents = "    Collections.Append"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents)
    )
    result = doc_highlight(completion_context)
    assert len(result) == 2
    data_regression.check(result, basename="test_document_highlight_keyword_namespace")


def test_document_highlight_generic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Keywords ***
My Keyword
    Log to console    Something

*** Test Cases ***
Test case 1
    Log    Something    IgnoreSomethingIgnore""",
    )

    line_contents = "    Log to console    Something"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 1
    )
    result = doc_highlight(completion_context)
    assert result
    assert len(result) == 2
    data_regression.check(result)


def test_document_highlight_variable(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Settings ***
Library    ${hh h}/my.py
Resource    ${hhh}/my.resource
Test Timeout    ${hh h}
Suite Setup    ${hhh}    ${hhh} Something
Suite Teardown    ${hhh}    ${hh h} Something hhh hh h h h

*** Variables ***
${h h h}    22

*** Test Cases ***
Test case 1
    Log    ${hhh}
    ${hhh}=    Log    ${h hh}    hhh ignore""",
    )

    line_contents = "    ${hhh}=    Log    ${h h"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents)
    )
    result = doc_highlight(completion_context)
    assert result
    assert len(result) == 11
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_variable_in_default_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Variables ***
${some var1}    1
${some var2}    2

*** Keywords ***
Put Key
    [Arguments]    ${key}    ${opts}=${some var1}
    ${ret}=    Create dictionary    ${key}=${some var2}
""",
    )

    line_contents = "    [Arguments]    ${key}    ${opts}=${som"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents)
    )
    result = doc_highlight(completion_context)
    assert len(result) == 2
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_variable_set_method(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Tasks ***
Minimal task
    Set local variable    $Cond1    1
    Log to Console    ${Cond1}
    Set local variable    ${Cond2}    2
    Log to Console    ${Cond2}
""",
    )

    line_contents = "    Log to Console    ${Cond2}"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents)
    )
    result = doc_highlight(completion_context)
    assert len(result) == 2
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_variable_set_method2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Tasks ***
Minimal task
    Set local variable    $Cond1    1
    Log to Console    ${Cond1}
    Set local variable    ${Cond2}    2
    Log to Console    ${Cond2}
""",
    )

    line_contents = "    Log to Console    ${Cond1}"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 2
    )
    result = doc_highlight(completion_context)
    assert len(result) == 2
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_variable_only_local(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
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
    result = doc_highlight(completion_context)
    assert len(result) == 2
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_argument_in_caller(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Keywords ***
My Keyword
    [Arguments]    ${Foo}
    Log    ${fOo}

*** Test Case ***
My Test
    My Keyword    foO=22
    """,
    )
    line = doc.find_line_with_contents("    Log    ${fOo}")
    col = len("    Log    ${fOo}") - 2
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = doc_highlight(completion_context)
    assert len(result) == 3
    data_regression.check(
        sorted(
            result,
            key=lambda entry: (
                entry["range"]["start"]["line"],
                entry["range"]["start"]["character"],
            ),
        )
    )


def test_document_highlight_unclosed_var(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.doc_highlight import doc_highlight

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Settings ***
Variables           ${CURDIR}${/common vari""",
    )
    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = doc_highlight(completion_context)
    assert len(result) == 0
