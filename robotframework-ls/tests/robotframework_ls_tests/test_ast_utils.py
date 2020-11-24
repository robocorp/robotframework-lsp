def test_iter_nodes():
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.robot_workspace import RobotDocument

    doc = RobotDocument(
        "unused", source="*** settings ***\nResource    my_resource.resource"
    )
    lst = []
    for stack, node in ast_utils._iter_nodes(doc.get_ast()):
        lst.append(
            "%s - %s" % ([s.__class__.__name__ for s in stack], node.__class__.__name__)
        )
    assert lst == [
        "[] - SettingSection",
        "['SettingSection'] - SettingSectionHeader",
        "['SettingSection'] - ResourceImport",
    ]


def test_print_ast(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl import ast_utils

    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO

    doc = RobotDocument("unused", source="*** settings ***")
    s = StringIO()
    ast_utils.print_ast(doc.get_ast(), stream=s)
    assert [
        x.replace("SETTING HEADER", "SETTING_HEADER") for x in s.getvalue().splitlines()
    ] == [
        "  File                                               (0, 0) -> (0, 16)",
        "    SettingSection                                   (0, 0) -> (0, 16)",
        "      SettingSectionHeader                           (0, 0) -> (0, 16)",
        "      - SETTING_HEADER, '*** settings ***'                  (0, 0->16)",
        "      - EOL, ''                                            (0, 16->16)",
    ]


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
