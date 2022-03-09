robot_framework_template_file = """
*** Settings ***
Library    XML    use_lxml=${True}
Library   SeleniumLibrary    WITH NAME    Selenium
Library    ${CURDIR}/subdirectory/my_library.py
Library    A.B

*** Test Cases ***

Test case name
    <PLACEHOLDER_TESTCASE_KEYWORD>
    

*** Keywords ***

Keyword that does something
    <PLACEHOLDER_KEYWORDS_KEYWORD>

""".replace(
    "\r\n", "\n"
).replace(
    "\r", "\n"
)


def set_test_case_with_keyword(keyword, workspace):
    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    robot_framework_source_file = robot_framework_template_file.replace(
        "<PLACEHOLDER_TESTCASE_KEYWORD>", keyword
    )
    doc.source = robot_framework_source_file
    return doc


def set_keyword_in_keyword_section(keyword, workspace):
    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    robot_framework_source_file = robot_framework_template_file.replace(
        "<PLACEHOLDER_KEYWORDS_KEYWORD>", keyword
    )
    doc.source = robot_framework_source_file
    return doc


def get_semantic_tokens_from_language_server(workspace, doc):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    decoded = decode_semantic_tokens(semantic_tokens, doc)
    grammar_token_mapping = convert_decoded_tokens_to_dictionary(decoded)
    return grammar_token_mapping


def convert_decoded_tokens_to_dictionary(decoded_tokens):
    grammar_token_mapping = {}
    for item in decoded_tokens:
        grammar_element = item[0]
        semantic_token_name = item[1]
        grammar_token_mapping[grammar_element] = semantic_token_name
    return grammar_token_mapping


def test_keyword_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword(
        "Parse XML    ${CURDIR}/my_file.xml", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("Parse XML") == "keywordNameCall"


def test_library_prefix_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword(
        "XML.Parse XML    ${CURDIR}/my_file.xml", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("XML") == "name"


def test_library_imported_with_name_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword(
        "Selenium.Open Browser    ${CURDIR}/my_file.xml", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("Selenium") == "name"
    assert semantic_tokens.get(".Open Browser") == "keywordNameCall"


def test_custom_library_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("my_library.Foobar", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("my_library") == "name"
    assert semantic_tokens.get(".Foobar") == "keywordNameCall"


def test_keyword_that_contains_dot_should_not_be_mistaken_for_library(workspace):
    robot_source_file = set_test_case_with_keyword(
        "Transport costs to destination are 389.50", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert not semantic_tokens.get("Transport costs to destination are 389")
    assert (
        semantic_tokens.get("Transport costs to destination are 389.50")
        == "keywordNameCall"
    )


def test_library_prefix_combined_with_dots_in_keyword(workspace):
    robot_source_file = set_test_case_with_keyword(
        "my_library.Open Version 1.0, workspace", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("my_library") == "name"
    assert semantic_tokens.get(".Open Version 1.0, workspace") == "keywordNameCall"


def test_library_name_in_dot_notation_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("A.B.Append to list", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("A.B") == "name"
    assert semantic_tokens.get(".Append to list") == "keywordNameCall"


def test_library_names_with_different_case_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword(
        "MY_LIBRARY.Open Version 1.0, workspace", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )

    assert semantic_tokens.get("MY_LIBRARY") == "name"
    assert semantic_tokens.get(".Open Version 1.0, workspace") == "keywordNameCall"
