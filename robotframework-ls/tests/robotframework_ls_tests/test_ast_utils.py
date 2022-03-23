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
            "[] - SettingSectionHeader",
            "[] - ResourceImport",
        ],
        [  # version 4.0.4 onwards
            "[] - SectionHeader",
            "[] - ResourceImport",
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
    for token in ast_utils.iter_expression_tokens(
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


def test_in_expression():
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    document = RobotDocument(
        "uri",
        """
*** Keyword **
my
    Run Keyword If   $v1 == ${v2}    CallThis""",
    )
    ast = document.get_ast()
    found = []
    for node_info in ast_utils.iter_indexed(ast, "KeywordCall"):
        handler = ast_utils.get_args_as_keywords_handler(node_info.node)
        for tok in node_info.node.tokens:
            if tok.type == tok.ARGUMENT:
                found.append(
                    f"is_kw {tok.value} = {handler.consider_current_argument_token_as_keyword(tok)}",
                )
                found.append(
                    f"was_exp {tok.value} = {handler.was_last_expression_argument}",
                )

    assert found == [
        "is_kw $v1 == ${v2} = False",
        "was_exp $v1 == ${v2} = True",
        "is_kw CallThis = True",
        "was_exp CallThis = False",
    ]


def test_in_expression_else_if():
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    document = RobotDocument(
        "uri",
        """
*** Keyword **
my
    Run Keyword If   $v1 == ${v2}    CallThis    ELSE IF    $v1 == ${v2}    CallThis""",
    )
    ast = document.get_ast()
    found = []
    for node_info in ast_utils.iter_indexed(ast, "KeywordCall"):
        handler = ast_utils.get_args_as_keywords_handler(node_info.node)
        for tok in node_info.node.tokens:
            if tok.type == tok.ARGUMENT:
                found.append(
                    f"is_kw {tok.value} = {handler.consider_current_argument_token_as_keyword(tok)}",
                )
                found.append(
                    f"was_exp {tok.value} = {handler.was_last_expression_argument}",
                )

    assert found == [
        "is_kw $v1 == ${v2} = False",
        "was_exp $v1 == ${v2} = True",
        "is_kw CallThis = True",
        "was_exp CallThis = False",
        "is_kw ELSE IF = False",
        "was_exp ELSE IF = False",
        "is_kw $v1 == ${v2} = False",
        "was_exp $v1 == ${v2} = True",
        "is_kw CallThis = True",
        "was_exp CallThis = False",
    ]
