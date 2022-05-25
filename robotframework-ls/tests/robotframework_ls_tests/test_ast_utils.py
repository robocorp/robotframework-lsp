def test_iter_nodes():
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused", source="*** settings ***\nResource    my_resource.resource"
    )
    lst = []
    for stack, node in ast_utils.iter_all_nodes_recursive(doc.get_ast()):
        lst.append(
            "%s - %s" % ([s.__class__.__name__ for s in stack], node.__class__.__name__)
        )
    assert lst in (
        [
            "[] - SettingSection",
            "['SettingSection'] - SettingSectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
        [  # version 4.0.4 onwards
            "[] - SettingSection",
            "['SettingSection'] - SectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
    )

    lst = []
    for stack, node in ast_utils._iter_nodes(doc.get_ast()):
        lst.append(
            "%s - %s" % ([s.__class__.__name__ for s in stack], node.__class__.__name__)
        )
    assert lst in (
        [
            "[] - SettingSection",
            "['SettingSection'] - SettingSectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
        [  # version 4.0.4 onwards
            "[] - SettingSection",
            "['SettingSection'] - SectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
    )

    lst = []
    for stack, node in ast_utils._iter_nodes(doc.get_ast(), recursive=False):
        lst.append(
            "%s - %s" % ([s.__class__.__name__ for s in stack], node.__class__.__name__)
        )
    assert lst == [
        "[] - SettingSection",
    ]

    lst = []
    for stack, node in ast_utils._iter_nodes(
        doc.get_ast().sections[0], recursive=False
    ):
        lst.append(
            "%s - %s" % ([s.__class__.__name__ for s in stack], node.__class__.__name__)
        )
    assert lst in (
        [
            "['SettingSection'] - SettingSectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
        [  # version 4.0.4 onwards
            "['SettingSection'] - SectionHeader",
            "['SettingSection'] - ResourceImport",
        ],
    )


def test_print_ast(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    from io import StringIO

    doc = RobotDocument("unused", source="*** settings ***")
    s = StringIO()
    ast_utils.print_ast(doc.get_ast(), stream=s)
    assert [
        x.replace("SETTING HEADER", "SETTING_HEADER") for x in s.getvalue().splitlines()
    ] in (
        [
            "  File                                               (0, 0) -> (0, 16)",
            "    SettingSection                                   (0, 0) -> (0, 16)",
            "      SettingSectionHeader                           (0, 0) -> (0, 16)",
            "      - SETTING_HEADER, '*** settings ***'                  (0, 0->16)",
            "      - EOL, ''                                            (0, 16->16)",
        ],
        [  # version 4.0.4 onwards
            "  File                                               (0, 0) -> (0, 16)",
            "    SettingSection                                   (0, 0) -> (0, 16)",
            "      SectionHeader                                  (0, 0) -> (0, 16)",
            "      - SETTING_HEADER, '*** settings ***'                  (0, 0->16)",
            "      - EOL, ''                                            (0, 16->16)",
        ],
    )


def test_find_token(workspace):
    """
    :param WorkspaceFixture workspace:
    """
    from robotframework_ls.impl import ast_utils

    workspace.set_root("case1")
    doc = workspace.get_doc("case1.robot")

    section = ast_utils.find_section(doc.get_ast(), 3)
    assert section.header.name == "Test Cases"

    token_info = ast_utils.find_token(section, 4, 1)
    assert token_info.token.type == token_info.token.TESTCASE_NAME
    assert token_info.token.value == "User can call library"

    token_info = ast_utils.find_token(section, 5, 7)
    assert token_info.token.type == token_info.token.KEYWORD
    assert token_info.token.value == "verify model"

    token_info = ast_utils.find_token(section, 50, 70)
    assert token_info is None


def test_ast_indexer_basic():
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import _ASTIndexer

    code = """
*** Settings ***
Library           Lib1
Library           Lib2

*** Keywords ***
Keyword 1
    Sleep    1

Keyword 2
    Sleep    1
"""
    document = RobotDocument("uri", code)
    indexer = _ASTIndexer(document.get_ast())
    assert len(list(indexer.iter_indexed("Keyword"))) == 2


def test_ast_indexer_only_setting():
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import _ASTIndexer

    code = """
*** Settings ***
Library           Lib1
Library           Lib2

*** Keywords ***
Keyword 1
    Sleep    1

Keyword 2
    Sleep    1
"""
    document = RobotDocument("uri", code)
    indexer = _ASTIndexer(document.get_ast())
    assert len(list(indexer.iter_indexed("LibraryImport"))) == 2
    assert len(list(indexer.iter_indexed("Keyword"))) == 2
    assert len(list(indexer.iter_indexed("SettingSection"))) == 1


def test_ast_extract_expression_variables(data_regression):
    from robotframework_ls.impl import ast_utils
    from robot.api import Token

    collected = []
    for token in ast_utils.iter_expression_variables(
        Token(Token.ARGUMENT, "$v1 > $v2 > ${v3}", 1, 0)
    ):
        collected.append(
            {
                "value": token.value,
                "lineno": token.lineno,
                "col_offset": token.col_offset,
            }
        )

    data_regression.check(collected)


def test_ast_extract_expression_tokens(data_regression):
    from robotframework_ls.impl import ast_utils
    from robot.api import Token

    collected = []
    for token, _var_info in ast_utils.iter_expression_tokens(
        Token(Token.ARGUMENT, "$v1 > ${v2} > ${v3} > $v4", 1, 0)
    ):
        collected.append(
            {
                "type": token.type,
                "value": token.value,
                "lineno": token.lineno,
                "col_offset": token.col_offset,
            }
        )

    data_regression.check(collected)


def check_value_and_tok_type(text, expected):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils_keyword_usage import (
        obtain_keyword_usage_handler,
    )

    document = RobotDocument(
        "uri",
        text,
    )
    ast = document.get_ast()
    found = []
    for node_info in ast_utils.iter_indexed(ast, "KeywordCall"):
        keyword_usage_handler = obtain_keyword_usage_handler(
            node_info.stack, node_info.node
        )
        for tok in node_info.node.tokens:
            if tok.type == tok.ARGUMENT:
                found.append(
                    f"{tok.value} = {keyword_usage_handler.get_token_type_as_str(tok)}",
                )

    assert found == expected


def test_in_expression():
    check_value_and_tok_type(
        """
*** Keyword **
my
    Run Keyword If   $v1 == ${v2}    CallThis
    """,
        [
            "$v1 == ${v2} = <expression>",
            "CallThis = <keyword>",
        ],
    )


def test_in_expression_else_if():
    check_value_and_tok_type(
        """
*** Keyword **
my
    Run Keyword If   $v1 == ${v2}    CallThis    ELSE IF    $v1 == ${v2}    CallThis""",
        [
            "$v1 == ${v2} = <expression>",
            "CallThis = <keyword>",
            "ELSE IF = <control>",
            "$v1 == ${v2} = <expression>",
            "CallThis = <keyword>",
        ],
    )


def test_for_each_input_work_item():
    check_value_and_tok_type(
        """
*** Keyword **
my
    For each input work item    No operation    items_limit=0    return_results=False    invalid_arg=True""",
        [
            "No operation = <keyword>",
            "items_limit=0 = <ignore>",
            "return_results=False = <ignore>",
            "invalid_arg=True = <none>",
        ],
    )


def test_run_keywords_1():
    check_value_and_tok_type(
        """
*** Keyword **
my
    Run Keywords   CallThis    Arg    AND    CallThis2""",
        [
            "CallThis = <keyword>",
            "Arg = <none>",
            "AND = <control>",
            "CallThis2 = <keyword>",
        ],
    )


def test_run_keywords_2():
    check_value_and_tok_type(
        """
*** Keyword **
my
    Run Keywords   CallThis    CallThis2""",
        [
            "CallThis = <keyword>",
            "CallThis2 = <keyword>",
        ],
    )


def check_keyword_usage_handler(text, data_regression, prefix_basename):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils_keyword_usage import (
        obtain_keyword_usage_handler,
    )

    document = RobotDocument(
        "uri",
        text,
    )
    ast = document.get_ast()
    found = []
    found_types = []
    line_col_to_usage = {}
    for node_info in ast_utils.iter_indexed(ast, "KeywordCall"):
        keyword_usage_handler = obtain_keyword_usage_handler(
            node_info.stack, node_info.node
        )

        for keyword_usage in keyword_usage_handler.iter_keyword_usages_from_node():
            toks = []
            for t in keyword_usage.node.tokens:
                key = (t.lineno, t.col_offset)
                if key not in line_col_to_usage:
                    line_col_to_usage[key] = keyword_usage
                toks.append(t.value)
            found.append(
                f"name:{keyword_usage.name}, is_arg_usage: {keyword_usage._is_argument_usage}, tokens: {', '.join(toks)}"
            )

        for token, token_type in keyword_usage_handler.iter_tokens_with_type():
            if token.value.strip():
                found_types.append(f"{token.value.strip()}, {token.type}, {token_type}")

    data_regression.check(found, basename=prefix_basename + "_usages")
    data_regression.check(found_types, basename=prefix_basename + "_types")

    for (line, col), kw_usage in line_col_to_usage.items():
        assert (
            keyword_usage_handler.get_keyword_usage_for_token_line_col(line, col)
            == kw_usage
        )


def test_run_keyword_in_run_keyword(data_regression):
    check_keyword_usage_handler(
        """
*** Keyword **
my
    Run keyword    Run keyword    Run Keyword    Log    foo""",
        data_regression,
        "test_run_keyword_in_run_keyword",
    )


def test_run_keyword_in_run_keyword_2(data_regression):
    check_keyword_usage_handler(
        """
*** Keyword **
my
    Run keywords    Run keyword    Log1    bar    AND    Run Keyword    Log2    foo""",
        data_regression,
        "test_run_keyword_in_run_keyword_2",
    )


def test_keyword_usage_stack():
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.robot_workspace import RobotDocument

    document = RobotDocument(
        "uri",
        """
*** Tasks ***
Minimal task
    Set local variable    $Cond1    1
    Log to Console    ${Cond1}
    Set local variable    ${Cond2}    2
    Log to Console    ${Cond2}
""",
    )

    ast = document.get_ast()
    test_sections = list(ast_utils.iter_test_case_sections(ast))
    assert len(test_sections) == 1
    test_section = next(iter(test_sections)).node

    tests = list(ast_utils.iter_tests(ast))
    assert len(tests) == 1
    test = next(iter(tests)).node

    for keyword_usage in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        assert keyword_usage.stack == (
            test_section,
            test,
        )

    for keyword_usage in ast_utils.iter_keyword_usage_tokens(
        test, collect_args_as_keywords=True
    ):
        assert keyword_usage.stack == (test,)


def test_variable_references_stack():
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.basic import isinstance_name

    document = RobotDocument(
        "uri",
        """
*** Variables ***
${VAR}            Variable value

*** Keywords ***
Keyword 1
    [Arguments]    ${a}=a    ${b}=b    ${c}=${a}
""",
    )

    ast = document.get_ast()
    refs = list(ast_utils.iter_variable_references(ast))
    assert len(refs) == 1
    var_info = next(iter(refs))
    assert var_info.token.value == "a"
    assert len(var_info.stack) == 1
    assert isinstance_name(var_info.stack[0], "Keyword")


def regression_check(data_regression, refs):
    from robocorp_ls_core.basic import isinstance_name

    refs = sorted(refs, key=lambda var_info: var_info.token.value)
    found = []
    for var_info in refs:
        found.append(str(var_info))
        assert isinstance_name(var_info.stack[-1], "Keyword")
    data_regression.check(found)


def test_variable_references_vars_in_var(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    document = RobotDocument(
        "uri",
        """
*** Keywords ***
Keyword 1
    Log    ${aa+${bb}}
""",
    )

    ast = document.get_ast()
    refs = list(ast_utils.iter_variable_references(ast))
    regression_check(data_regression, refs)


def test_variable_references_vars_in_var_2(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    document = RobotDocument(
        "uri",
        """
*** Keywords ***
Keyword 1
    Log    @{OBJJ.name}
""",
    )

    ast = document.get_ast()
    refs = list(ast_utils.iter_variable_references(ast))
    regression_check(data_regression, refs)
