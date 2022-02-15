from typing import List
from robocorp_ls_core.protocols import IDocument
import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version


def check(found, expected):
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import ast_utils
    import robot

    semantic_tokens_as_int: List[int] = found[0]
    doc: IDocument = found[1]
    decoded = decode_semantic_tokens(semantic_tokens_as_int, doc)
    if decoded != expected:
        from io import StringIO

        stream = StringIO()
        ast_utils.print_ast(CompletionContext(doc).get_ast(), stream=stream)
        raise AssertionError(
            "Expected:\n%s\n\nFound:\n%s\n\nAst:\n%s\n\nRobot: %s %s"
            % (expected, decoded, stream.getvalue(), robot.get_version(), robot)
        )


def test_semantic_highlighting_base(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library   my.lib

*** Keywords ***
Some Keyword
    [Arguments]     Some ${arg1}     Another ${arg2}
    Clear All Highlights    ${arg1}    ${arg2}
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("my.lib", "name"),
            ("*** Keywords ***", "header"),
            ("Some Keyword", "keywordNameDefinition"),
            ("[", "variableOperator"),
            ("Arguments", "setting"),
            ("]", "variableOperator"),
            ("Some ", "argumentValue"),
            ("${", "variableOperator"),
            ("arg1", "variable"),
            ("}", "variableOperator"),
            ("Another ", "argumentValue"),
            ("${", "variableOperator"),
            ("arg2", "variable"),
            ("}", "variableOperator"),
            ("Clear All Highlights", "keywordNameCall"),
            ("${", "variableOperator"),
            ("arg1", "variable"),
            ("}", "variableOperator"),
            ("${", "variableOperator"),
            ("arg2", "variable"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_highlighting_arguments(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """
*** Test Cases ***
Some Test
    Clear All Highlights    formatter=some ${arg1} other
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Test Cases ***", "header"),
            ("Some Test", "testCaseName"),
            ("Clear All Highlights", "keywordNameCall"),
            ("formatter", "parameterName"),
            ("=", "variableOperator"),
            ("some ", "argumentValue"),
            ("${", "variableOperator"),
            ("arg1", "variable"),
            ("}", "variableOperator"),
            (" other", "argumentValue"),
        ],
    )


def test_semantic_highlighting_arguments_in_doc(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """
*** Settings ***
Documentation    Some = eq
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Documentation", "setting"),
            ("Some = eq", "documentation"),
        ],
    )


def test_semantic_highlighting_keyword(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Keywords ***
Some Keyword
    [Arguments]     ${arg1}
    Call Keyword    ${arg1}
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Keywords ***", "header"),
            ("Some Keyword", "keywordNameDefinition"),
            ("[", "variableOperator"),
            ("Arguments", "setting"),
            ("]", "variableOperator"),
            ("${", "variableOperator"),
            ("arg1", "variable"),
            ("}", "variableOperator"),
            ("Call Keyword", "keywordNameCall"),
            ("${", "variableOperator"),
            ("arg1", "variable"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_highlighting_task_name(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Task ***
Some Task
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [("*** Task ***", "header"), ("Some Task", "testCaseName")],
    )


def test_semantic_highlighting_comments(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Comments ***
Comment part 1
Comment part 2
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Comments ***", "header"),
            ("Comment part 1", "comment"),
            ("Comment part 2", "comment"),
        ],
    )


def test_semantic_highlighting_catenate(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Test Case ***
Test Case
    Catenate    FOO
    ...            Check = 22
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Test Case ***", "header"),
            ("Test Case", "testCaseName"),
            ("Catenate", "keywordNameCall"),
            ("FOO", "argumentValue"),
            ("Check = 22", "argumentValue"),
        ],
    )


def test_semantic_highlighting_on_keyword_argument(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Test Case ***
Test Case
    Run Keyword If    ${var}    Should Be Empty
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Test Case ***", "header"),
            ("Test Case", "testCaseName"),
            ("Run Keyword If", "keywordNameCall"),
            ("${", "variableOperator"),
            ("var", "variable"),
            ("}", "variableOperator"),
            ("Should Be Empty", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_errors(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** invalid invalid ***
Foo
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [("*** invalid invalid ***", "error"), ("Foo", "comment")],
    )


def test_semantic_highlighting_dotted_access_to_keyword(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library    Collections     WITH NAME     Col

*** Test Cases ***
Test case 1
    Col.Append to list
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("Collections", "name"),
            ("WITH NAME", "control"),
            ("Col", "name"),
            ("*** Test Cases ***", "header"),
            ("Test case 1", "testCaseName"),
            ("Col", "name"),
            ("Append to list", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_dotted_access_to_keyword_suite_setup(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library    Collections     WITH NAME     Col
Suite Setup    Col.Append to list

*** Test Cases ***
Some test
    [Setup]     Col.Append to list
    Col.Append to list
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("Collections", "name"),
            ("WITH NAME", "control"),
            ("Col", "name"),
            ("Suite Setup", "setting"),
            ("Col", "name"),
            ("Append to list", "keywordNameCall"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Setup", "setting"),
            ("]", "variableOperator"),
            ("Col", "name"),
            ("Append to list", "keywordNameCall"),
            ("Col", "name"),
            ("Append to list", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_dotted_access_to_keyword_suite_setup_2(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Library    A.B
Suite Setup    A.B.Append to list

*** Test Cases ***
Some test
    [Setup]     A.B.Append to list
    A.B.Append to list
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("A.B", "name"),
            ("Suite Setup", "setting"),
            ("A.B", "name"),
            ("Append to list", "keywordNameCall"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Setup", "setting"),
            ("]", "variableOperator"),
            ("A.B", "name"),
            ("Append to list", "keywordNameCall"),
            ("A.B", "name"),
            ("Append to list", "keywordNameCall"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards")
def test_semantic_highlighting_try_except(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Test cases ***
Try except inside try
    TRY
        TRY
            Fail    nested failure
        EXCEPT    miss
            Fail    Should not be executed
        ELSE
            No operation
        FINALLY
            Log    in the finally
        END
    EXCEPT    nested failure
        No operation
    END
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Test cases ***", "header"),
            ("Try except inside try", "testCaseName"),
            ("TRY", "control"),
            ("TRY", "control"),
            ("Fail", "keywordNameCall"),
            ("nested failure", "argumentValue"),
            ("EXCEPT", "control"),
            ("miss", "argumentValue"),
            ("Fail", "keywordNameCall"),
            ("Should not be executed", "argumentValue"),
            ("ELSE", "control"),
            ("No operation", "keywordNameCall"),
            ("FINALLY", "control"),
            ("Log", "keywordNameCall"),
            ("in the finally", "argumentValue"),
            ("END", "control"),
            ("EXCEPT", "control"),
            ("nested failure", "argumentValue"),
            ("No operation", "keywordNameCall"),
            ("END", "control"),
        ],
    )


def test_semantic_highlighting_documentation(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    Some documentation
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Documentation", "setting"),
            ("Docs in settings", "documentation"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Documentation", "setting"),
            ("]", "variableOperator"),
            ("Some documentation", "documentation"),
        ],
    )


def test_semantic_highlighting_vars_in_documentation(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    ${my var} Some documentation
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Documentation", "setting"),
            ("Docs in settings", "documentation"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Documentation", "setting"),
            ("]", "variableOperator"),
            ("${", "variableOperator"),
            ("my var", "variable"),
            ("}", "variableOperator"),
            (" Some documentation", "documentation"),
        ],
    )


def test_semantic_highlighting_vars_in_documentation_incomplete(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    ${my var Some documentation
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Settings ***", "header"),
            ("Documentation", "setting"),
            ("Docs in settings", "documentation"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Documentation", "setting"),
            ("]", "variableOperator"),
            ("${my var Some documentation", "documentation"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards")
def test_semantic_highlighting_while(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Variables ***
${variable}    ${1}

*** Test Cases ***
While loop executed once
    WHILE    $variable < 2
        Log    ${variable}
        ${variable}=    Evaluate    $variable + 1
    END
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Variables ***", "header"),
            ("${", "variableOperator"),
            ("variable", "variable"),
            ("}", "variableOperator"),
            ("${", "variableOperator"),
            ("1", "variable"),
            ("}", "variableOperator"),
            ("*** Test Cases ***", "header"),
            ("While loop executed once", "testCaseName"),
            ("WHILE", "control"),
            ("$variable < 2", "argumentValue"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("variable", "variable"),
            ("}", "variableOperator"),
            ("${variable}=", "control"),
            ("Evaluate", "keywordNameCall"),
            ("$variable + 1", "argumentValue"),
            ("END", "control"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards")
def test_semantic_highlighting_for_if(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Keywords ***
Some keyword
    FOR    ${element}    IN       @{LIST}
        IF    ${random} == ${NUMBER_TO_PASS_ON}
            Pass Execution    "${random} == ${NUMBER_TO_PASS_ON}"
        ELSE IF    ${random} > ${NUMBER_TO_PASS_ON}
            Log To Console    Too high.
        ELSE
            Log To Console    Too low.
        END
    END
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)

    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        [
            ("*** Keywords ***", "header"),
            ("Some keyword", "keywordNameDefinition"),
            ("FOR", "control"),
            ("${", "variableOperator"),
            ("element", "variable"),
            ("}", "variableOperator"),
            ("IN", "control"),
            ("@{", "variableOperator"),
            ("LIST", "variable"),
            ("}", "variableOperator"),
            ("IF", "control"),
            ("${", "variableOperator"),
            ("random", "variable"),
            ("}", "variableOperator"),
            (" == ", "argumentValue"),
            ("${", "variableOperator"),
            ("NUMBER_TO_PASS_ON", "variable"),
            ("}", "variableOperator"),
            ("Pass Execution", "keywordNameCall"),
            ('"', "argumentValue"),
            ("${", "variableOperator"),
            ("random", "variable"),
            ("}", "variableOperator"),
            (" == ", "argumentValue"),
            ("${", "variableOperator"),
            ("NUMBER_TO_PASS_ON", "variable"),
            ("}", "variableOperator"),
            ('"', "argumentValue"),
            ("ELSE IF", "control"),
            ("${", "variableOperator"),
            ("random", "variable"),
            ("}", "variableOperator"),
            (" > ", "argumentValue"),
            ("${", "variableOperator"),
            ("NUMBER_TO_PASS_ON", "variable"),
            ("}", "variableOperator"),
            ("Log To Console", "keywordNameCall"),
            ("Too high.", "argumentValue"),
            ("ELSE", "control"),
            ("Log To Console", "keywordNameCall"),
            ("Too low.", "argumentValue"),
            ("END", "control"),
            ("END", "control"),
        ],
    )
