def test_ast_to_code():
    from robotframework_interactive.ast_to_code import ast_to_code
    from robot.api import get_model

    code = (
        "*** Settings ***\n"
        "Library     lib    WITH NAME    foo\n"
        "\n"
        "*** Comments ***\n"
        "some comment\n"
        "\n"
        "*** Test Cases ***\n"
        "Test\n"
        "        [Documentation]        doc\n"
        "        [Tags]        sometag\n"
        "        Pass\n"
        "        Keyword\n"
        "        One More\n"
        "        Multiline    check1\n"
        "        ...          check2\n"
    )
    model = get_model(code)
    assert ast_to_code(model) == code


def test_ast_to_code_trim_lines_at_end():
    from robotframework_interactive.ast_to_code import ast_to_code
    from robot.api import get_model

    code = (
        "*** Test Cases ***\n"
        "Test\n"
        "    Keyword Call\n"
        "    \n"
        "    \n"
        "    \n"
        "    \n"
    )
    expected_code = "*** Test Cases ***\n" "Test\n" "    Keyword Call\n"
    model = get_model(code)
    assert ast_to_code(model) == expected_code
