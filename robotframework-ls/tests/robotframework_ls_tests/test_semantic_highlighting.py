from typing import List
from robocorp_ls_core.protocols import IDocument
import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version
import itertools


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

        compare_stream = StringIO()
        found_diff = False
        compare_stream.write("Found".ljust(40))
        compare_stream.write("Expected".ljust(40))
        compare_stream.write("\n")
        for a, b in itertools.zip_longest(decoded, expected, fillvalue=""):
            if not found_diff and str(a) != str(b):
                found_diff = True  # Just highlight the first difference
                compare_stream.write("! ")
            else:
                compare_stream.write("  ")

            compare_stream.write(str(a).ljust(40))
            compare_stream.write(str(b).ljust(40))
            compare_stream.write("\n")

        raise AssertionError(
            "Ast:\n%s\n\nRobot: %s %s\nExpected:\n%s\n\nFound:\n%s\n\n\nCompare:\n%s"
            % (
                stream.getvalue(),
                robot.get_version(),
                robot,
                expected,
                decoded,
                compare_stream.getvalue(),
            )
        )


def _setup_doc(workspace, source, root="case1", name="case1.robot"):
    workspace.set_root(root)
    doc = workspace.put_doc(name)
    doc.source = source
    return doc


def _create_ctx_and_check(workspace, doc, expected):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    check(
        (semantic_tokens, doc),
        expected,
    )


def check_simple(workspace, source, expected, root="case1", name="case1.robot"):
    doc = _setup_doc(workspace, source, root, name)
    _create_ctx_and_check(workspace, doc, expected)


def test_library_highlighting_resource(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Resource    some_resource.robot

*** Test Cases ***
Some test
    some_resource.Some Keyword
""",
        [
            ("*** Settings ***", "header"),
            ("Resource", "setting"),
            ("some_resource.robot", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("some_resource", "name"),
            (".Some Keyword", "keywordNameCall"),
        ],
    )


def test_library_highlighting_resource_casing(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Resource    some_resource.robot

*** Test Cases ***
Some test
    Some_REsource.Some Keyword
""",
        [
            ("*** Settings ***", "header"),
            ("Resource", "setting"),
            ("some_resource.robot", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Some_REsource", "name"),
            (".Some Keyword", "keywordNameCall"),
        ],
    )


def test_library_highlighting_resource_no_match(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Resource    some_resource.robot

*** Test Cases ***
Some test
    someresource.Some Keyword
""",
        [
            ("*** Settings ***", "header"),
            ("Resource", "setting"),
            ("some_resource.robot", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("someresource.Some Keyword", "keywordNameCall"),
        ],
    )


def test_library_highlighting_deps_basic(workspace):
    doc = _setup_doc(
        workspace,
        """
*** Settings ***
Resource    another_import.robot

*** Test Cases ***
Some test
    Collections.Insert into list
""",
    )

    another_doc = workspace.put_doc("another_import.robot")
    another_doc.source = """*** Settings ***
Library    Collections
"""

    _create_ctx_and_check(
        workspace,
        doc,
        [
            ("*** Settings ***", "header"),
            ("Resource", "setting"),
            ("another_import.robot", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Collections", "name"),
            (".Insert into list", "keywordNameCall"),
        ],
    )


def test_resource_highlighting_deps(workspace):
    doc = _setup_doc(
        workspace,
        """
*** Settings ***
Resource    ./resources/resource_in_pythonpath.robot

*** Test Cases ***
Some test
    resource_in_pythonpath.Keyword in Pythonpath
""",
        root="case_search_pythonpath_resource",
        name="root.robot",
    )

    _create_ctx_and_check(
        workspace,
        doc,
        [
            ("*** Settings ***", "header"),
            ("Resource", "setting"),
            ("./resources/resource_in_pythonpath.robot", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("resource_in_pythonpath", "name"),
            (".Keyword in Pythonpath", "keywordNameCall"),
        ],
    )


def test_library_highlighting_deps_1(workspace):
    doc = _setup_doc(
        workspace,
        """
*** Settings ***
Library    libraries.lib_in_pythonpath

*** Test Cases ***
Some test
    libraries.lib_in_pythonpath.find in library
""",
        root="case_search_pythonpath",
        name="root.robot",
    )

    _create_ctx_and_check(
        workspace,
        doc,
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("libraries.lib_in_pythonpath", "name"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("libraries.lib_in_pythonpath", "name"),
            (".find in library", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_base(workspace):
    check_simple(
        workspace,
        """*** Settings ***
Library   my.lib

*** Keywords ***
Some Keyword
    [Arguments]     Some ${arg1}     Another ${arg2}
    Clear All Highlights    ${arg1}    ${arg2}
""",
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
    check_simple(
        workspace,
        """
*** Test Cases ***
Some Test
    Clear All Highlights    formatter=some ${arg1} other
""",
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


def test_semantic_highlighting_vars_in_call(workspace):
    check_simple(
        workspace,
        """
*** Keyword ***
Some ${val} in arg
    Log to console    ${val}
        
*** Test Cases ***
Some Test
    ${val}=    Set variable    2
    Some ${val} in arg
""",
        [
            ("*** Keyword ***", "header"),
            ("Some ", "keywordNameDefinition"),
            ("${", "variableOperator"),
            ("val", "variable"),
            ("}", "variableOperator"),
            (" in arg", "keywordNameDefinition"),
            ("Log to console", "keywordNameCall"),
            ("${", "variableOperator"),
            ("val", "variable"),
            ("}", "variableOperator"),
            ("*** Test Cases ***", "header"),
            ("Some Test", "testCaseName"),
            ("${", "variableOperator"),
            ("val", "variable"),
            ("}", "variableOperator"),
            ("=", "variableOperator"),
            ("Set variable", "keywordNameCall"),
            ("2", "argumentValue"),
            ("Some ", "keywordNameCall"),
            ("${", "variableOperator"),
            ("val", "variable"),
            ("}", "variableOperator"),
            (" in arg", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_var_with_modifier(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Log    ${A}[1]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("A", "variable"),
            ("}[", "variableOperator"),
            ("1", "variable"),
            ("]", "variableOperator"),
        ],
    )


def test_semantic_highlighting_var_with_modifier_2(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Log    ${A VAR ${A}}
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("A VAR ", "variable"),
            ("${", "variableOperator"),
            ("A", "variable"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_highlighting_var_with_modifier_3(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Log    ${A}[${{["\["]}}]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("A", "variable"),
            ("}[", "variableOperator"),
            ("${", "variableOperator"),
            ("{", "variableOperator"),
            ('["\\["]', "argumentValue"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
            ("]", "variableOperator"),
        ],
    )


def test_semantic_highlighting_var_with_modifier_4(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Log    ${A}[${{$a}}]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("A", "variable"),
            ("}[", "variableOperator"),
            ("${", "variableOperator"),
            ("{", "variableOperator"),
            ("$", "variableOperator"),
            ("a", "variable"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
            ("]", "variableOperator"),
        ],
    )


def test_semantic_highlighting_var_with_modifier_1(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Log    ${AA ${BB} CC}[${DD}]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            # var
            ("AA ", "variable"),
            ("${", "variableOperator"),
            # var
            ("BB", "variable"),
            ("}", "variableOperator"),
            # var
            (" CC", "variable"),
            ("}[", "variableOperator"),
            ("${", "variableOperator"),
            # var
            ("DD", "variable"),
            ("}", "variableOperator"),
            ("]", "variableOperator"),
        ],
    )


def test_semantic_highlighting_run_keyword_if_basic(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Run Keyword If    ${Cond1}    No operation    ELSE    No operation
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Run Keyword If", "keywordNameCall"),
            ("${", "variableOperator"),
            ("Cond1", "variable"),
            ("}", "variableOperator"),
            ("No operation", "keywordNameCall"),
            ("ELSE", "control"),
            ("No operation", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_run_keyword_if_2(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Some test
    Run Keyword If    ${Cond1}    No operation    ELSE IF   ${cond}    No operation    arg    ELSE    No operation     arg
""",
        [
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("Run Keyword If", "keywordNameCall"),
            ("${", "variableOperator"),
            ("Cond1", "variable"),
            ("}", "variableOperator"),
            ("No operation", "keywordNameCall"),
            ("ELSE IF", "control"),
            ("${", "variableOperator"),
            ("cond", "variable"),
            ("}", "variableOperator"),
            ("No operation", "keywordNameCall"),
            ("arg", "argumentValue"),
            ("ELSE", "control"),
            ("No operation", "keywordNameCall"),
            ("arg", "argumentValue"),
        ],
    )


def test_semantic_highlighting_arguments_in_doc(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Documentation    Some = eq
""",
        [
            ("*** Settings ***", "header"),
            ("Documentation", "setting"),
            ("Some = eq", "documentation"),
        ],
    )


def test_semantic_highlighting_keyword(workspace):
    check_simple(
        workspace,
        """*** Keywords ***
Some Keyword
    [Arguments]     ${arg1}
    Call Keyword    ${arg1}
""",
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
    check_simple(
        workspace,
        """*** Task ***
Some Task
""",
        [("*** Task ***", "header"), ("Some Task", "testCaseName")],
    )


def test_semantic_highlighting_comments(workspace):
    check_simple(
        workspace,
        """*** Comments ***
Comment part 1
Comment part 2
""",
        [
            ("*** Comments ***", "header"),
            ("Comment part 1", "comment"),
            ("Comment part 2", "comment"),
        ],
    )


def test_semantic_highlighting_comment_keyword(workspace):
    check_simple(
        workspace,
        """*** Test Cases ***
Check
    Comment    ${var} Set Variable Test
""",
        [
            ("*** Test Cases ***", "header"),
            ("Check", "testCaseName"),
            ("Comment", "keywordNameCall"),
            ("${", "variableOperator"),
            ("var", "variable"),
            ("}", "variableOperator"),
            (" Set Variable Test", "documentation"),
        ],
    )


def test_semantic_highlighting_catenate(workspace):
    check_simple(
        workspace,
        """*** Test Case ***
Test Case
    Catenate    FOO
    ...            Check = 22
""",
        [
            ("*** Test Case ***", "header"),
            ("Test Case", "testCaseName"),
            ("Catenate", "keywordNameCall"),
            ("FOO", "argumentValue"),
            ("Check = 22", "argumentValue"),
        ],
    )


def test_semantic_highlighting_on_keyword_argument(workspace):
    check_simple(
        workspace,
        """*** Test Case ***
Test Case
    Run Keyword If    ${var}    Should Be Empty
""",
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
    check_simple(
        workspace,
        """*** invalid invalid ***
Foo
""",
        [("*** invalid invalid ***", "error"), ("Foo", "comment")],
    )


def test_semantic_highlighting_dotted_access_to_keyword(workspace):
    check_simple(
        workspace,
        """*** Settings ***
Library    Collections     WITH NAME     Col

*** Test Cases ***
Test case 1
    Col.Append to list
""",
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("Collections", "name"),
            ("WITH NAME", "control"),
            ("Col", "name"),
            ("*** Test Cases ***", "header"),
            ("Test case 1", "testCaseName"),
            ("Col", "name"),
            (".Append to list", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_dotted_access_to_keyword_suite_setup(workspace):
    check_simple(
        workspace,
        """*** Settings ***
Library    Collections     WITH NAME     Col
Suite Setup    Col.Append to list

*** Test Cases ***
Some test
    [Setup]     Col.Append to list
    Col.Append to list
""",
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("Collections", "name"),
            ("WITH NAME", "control"),
            ("Col", "name"),
            ("Suite Setup", "setting"),
            ("Col", "name"),
            (".Append to list", "keywordNameCall"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Setup", "setting"),
            ("]", "variableOperator"),
            ("Col", "name"),
            (".Append to list", "keywordNameCall"),
            ("Col", "name"),
            (".Append to list", "keywordNameCall"),
        ],
    )


def test_semantic_highlighting_dotted_access_to_keyword_suite_setup_2(workspace):
    check_simple(
        workspace,
        """*** Settings ***
Library    A.B
Suite Setup    A.B.Append to list

*** Test Cases ***
Some test
    [Setup]     A.B.Append to list
    A.B.Append to list
""",
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("A.B", "name"),
            ("Suite Setup", "setting"),
            ("A.B", "name"),
            (".Append to list", "keywordNameCall"),
            ("*** Test Cases ***", "header"),
            ("Some test", "testCaseName"),
            ("[", "variableOperator"),
            ("Setup", "setting"),
            ("]", "variableOperator"),
            ("A.B", "name"),
            (".Append to list", "keywordNameCall"),
            ("A.B", "name"),
            (".Append to list", "keywordNameCall"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards")
def test_semantic_highlighting_try_except(workspace):
    check_simple(
        workspace,
        """*** Test cases ***
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
""",
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
    check_simple(
        workspace,
        """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    Some documentation
""",
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
    check_simple(
        workspace,
        """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    ${my var} Some documentation
""",
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
    check_simple(
        workspace,
        """*** Settings ***
Documentation    Docs in settings

*** Test Cases ***
Some test
    [Documentation]    ${my var Some documentation
""",
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
    check_simple(
        workspace,
        """*** Variables ***
${variable}    ${1}

*** Test Cases ***
While loop executed once
    WHILE    $variable < 2
        Log    ${variable}
        ${variable}=    Evaluate    $variable + 1
    END
""",
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
            ("$", "variableOperator"),
            ("variable", "variable"),
            (" < 2", "argumentValue"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("variable", "variable"),
            ("}", "variableOperator"),
            ("${", "variableOperator"),
            ("variable", "variable"),
            ("}", "variableOperator"),
            ("=", "variableOperator"),
            ("Evaluate", "keywordNameCall"),
            ("$", "variableOperator"),
            ("variable", "variable"),
            (" + 1", "argumentValue"),
            ("END", "control"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards")
def test_semantic_highlighting_while_limit(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
While loop
    WHILE    $variable < 2    limit=10
        No operation
    END
""",
        [
            ("*** Test Cases ***", "header"),
            ("While loop", "testCaseName"),
            ("WHILE", "control"),
            ("$", "variableOperator"),
            ("variable", "variable"),
            (" < 2", "argumentValue"),
            ("limit", "parameterName"),
            ("=", "variableOperator"),
            ("10", "argumentValue"),
            ("No operation", "keywordNameCall"),
            ("END", "control"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards")
def test_semantic_highlighting_except_type(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Glob pattern
    TRY
        Some Keyword
    EXCEPT    ValueError: *    type=GLOB
""",
        [
            ("*** Test Cases ***", "header"),
            ("Glob pattern", "testCaseName"),
            ("TRY", "control"),
            ("Some Keyword", "keywordNameCall"),
            ("EXCEPT", "control"),
            ("ValueError: *", "argumentValue"),
            ("type", "parameterName"),
            ("=", "variableOperator"),
            ("GLOB", "argumentValue"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards")
def test_semantic_highlighting_for_if(workspace):
    check_simple(
        workspace,
        """*** Keywords ***
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
""",
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


def test_semantic_highlighting_for(workspace):
    check_simple(
        workspace,
        """*** Keywords ***
Some keyword
    FOR    ${e1}    ${e2}    IN       &{DCT}
        No operation
    END
""",
        [
            ("*** Keywords ***", "header"),
            ("Some keyword", "keywordNameDefinition"),
            ("FOR", "control"),
            ("${", "variableOperator"),
            ("e1", "variable"),
            ("}", "variableOperator"),
            ("${", "variableOperator"),
            ("e2", "variable"),
            ("}", "variableOperator"),
            ("IN", "control"),
            ("&{", "variableOperator"),
            ("DCT", "variable"),
            ("}", "variableOperator"),
            ("No operation", "keywordNameCall"),
            ("END", "control"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 5 onwards")
def test_semantic_highlighting_expressions(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Example
    IF    $rc > 0
        Op
    ELSE IF    $rc < ${rc2}
        Op2
    ELSE
        Fail    Unexpected rc: ${rc}
    END
""",
        [
            ("*** Test Cases ***", "header"),
            ("Example", "testCaseName"),
            ("IF", "control"),
            ("$", "variableOperator"),
            ("rc", "variable"),
            (" > 0", "argumentValue"),
            ("Op", "keywordNameCall"),
            ("ELSE IF", "control"),
            ("$", "variableOperator"),
            ("rc", "variable"),
            (" < ", "argumentValue"),
            ("${", "variableOperator"),
            ("rc2", "variable"),
            ("}", "variableOperator"),
            ("Op2", "keywordNameCall"),
            ("ELSE", "control"),
            ("Fail", "keywordNameCall"),
            ("Unexpected rc: ", "argumentValue"),
            ("${", "variableOperator"),
            ("rc", "variable"),
            ("}", "variableOperator"),
            ("END", "control"),
        ],
    )


def test_semantic_highlighting_expression_evaluate(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Example
    Evaluate   $v1 == ${v2}
""",
        [
            ("*** Test Cases ***", "header"),
            ("Example", "testCaseName"),
            ("Evaluate", "keywordNameCall"),
            ("$", "variableOperator"),
            ("v1", "variable"),
            (" == ", "argumentValue"),
            ("${", "variableOperator"),
            ("v2", "variable"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_highlighting_expression_keyword_if(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Example
    Run Keyword If   $v1 == ${v2}    Log to console    Foo
""",
        [
            ("*** Test Cases ***", "header"),
            ("Example", "testCaseName"),
            ("Run Keyword If", "keywordNameCall"),
            ("$", "variableOperator"),
            ("v1", "variable"),
            (" == ", "argumentValue"),
            ("${", "variableOperator"),
            ("v2", "variable"),
            ("}", "variableOperator"),
            ("Log to console", "keywordNameCall"),
            ("Foo", "argumentValue"),
        ],
    )


def test_semantic_highlighting_inner_exp(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Example
    Log to console    ${{$a == ${b}}}
""",
        [
            ("*** Test Cases ***", "header"),
            ("Example", "testCaseName"),
            ("Log to console", "keywordNameCall"),
            ("${", "variableOperator"),
            ("{", "variableOperator"),
            ("$", "variableOperator"),
            ("a", "variable"),
            (" == ", "argumentValue"),
            ("${", "variableOperator"),
            ("b", "variable"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_multiple_inner_vars(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Example
    Log    ${a+${b}+${c}}
""",
        [
            ("*** Test Cases ***", "header"),
            ("Example", "testCaseName"),
            ("Log", "keywordNameCall"),
            ("${", "variableOperator"),
            ("a+", "variable"),
            ("${", "variableOperator"),
            ("b", "variable"),
            ("}", "variableOperator"),
            ("+", "variable"),
            ("${", "variableOperator"),
            ("c", "variable"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
        ],
    )


def test_semantic_items(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[Address][Zip]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Dictionary Variable", "testCaseName"),
            ("Log to Console", "keywordNameCall"),
            ("${", "variableOperator"),
            ("Person", "variable"),
            ("}[", "variableOperator"),
            ("Address", "variable"),
            ("][", "variableOperator"),
            ("Zip", "variable"),
            ("]", "variableOperator"),
        ],
    )


def test_empty_base(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Dictionary Variable
    Log to Console    ${}[Address][Zip]
""",
        [
            ("*** Test Cases ***", "header"),
            ("Dictionary Variable", "testCaseName"),
            ("Log to Console", "keywordNameCall"),
            ("${", "variableOperator"),
            ("", "variable"),
            ("}[", "variableOperator"),
            ("Address", "variable"),
            ("][", "variableOperator"),
            ("Zip", "variable"),
            ("]", "variableOperator"),
        ],
    )


def test_semantic_and_in_run_keywords(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Suite Teardown     Run Keywords    Log     Tear1     AND     Log     Tear2

""",
        [
            ("*** Settings ***", "header"),
            ("Suite Teardown", "setting"),
            ("Run Keywords", "keywordNameCall"),
            ("Log", "keywordNameCall"),
            ("Tear1", "argumentValue"),
            ("AND", "control"),
            ("Log", "keywordNameCall"),
            ("Tear2", "argumentValue"),
        ],
    )


def test_semantic_with_slash(workspace):
    check_simple(
        workspace,
        """
*** Settings ***
Library    OperatingSystem

*** Test Case ***
My Test
    OperatingSystem.Create File    c:/temp/a.txt
    OperatingSystem.Append To File    c:/temp/a.txt    xxx=\\n
""",
        [
            ("*** Settings ***", "header"),
            ("Library", "setting"),
            ("OperatingSystem", "name"),
            ("*** Test Case ***", "header"),
            ("My Test", "testCaseName"),
            ("OperatingSystem", "name"),
            (".Create File", "keywordNameCall"),
            ("c:/temp/a.txt", "argumentValue"),
            ("OperatingSystem", "name"),
            (".Append To File", "keywordNameCall"),
            ("c:/temp/a.txt", "argumentValue"),
            ("xxx", "parameterName"),
            ("=", "variableOperator"),
            ("\\n", "argumentValue"),
        ],
    )


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards")
def test_semantic_var_in_expr(workspace):
    check_simple(
        workspace,
        """
*** Test Cases ***
Demo
    IF    ${{$var1 != "1"}}
        Fail
    END
""",
        [
            ("*** Test Cases ***", "header"),
            ("Demo", "testCaseName"),
            ("IF", "control"),
            ("${", "variableOperator"),
            ("{", "variableOperator"),
            ("$", "variableOperator"),
            ("var1", "variable"),
            (' != "1"', "argumentValue"),
            ("}", "variableOperator"),
            ("}", "variableOperator"),
            ("Fail", "keywordNameCall"),
            ("END", "control"),
        ],
    )
