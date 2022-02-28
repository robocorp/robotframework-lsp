from robotframework_ls.impl.completion_context import CompletionContext
from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

robot_framework_template_file = """
** Settings ***
Resource    name.resource

*** Test Cases ***

This is a test case definition
    Given Some prerequisites
    When Some action is taken on the system
    Then Some post condition is met

*** Keywords ***
  
This is a keyword function definition
    <PLACEHOLDER_KEYWORDS_KEYWORD>

""".replace(
    "\r\n", "\n"
).replace(
    "\r", "\n"
)


def set_keyword_in_keyword_section(keyword, workspace):
    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    robot_framework_source_file = robot_framework_template_file.replace(
        "<PLACEHOLDER_KEYWORDS_KEYWORD>", keyword
    )
    doc.source = robot_framework_source_file
    return doc


def get_semantic_tokens_from_language_server(workspace, doc):
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
        print(item[0] + " - " + item[1])
    return grammar_token_mapping


def test_bdd_statement_at_start_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "The element WriteOff has the value ${value}", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert (
        semantic_tokens.get("The element WriteOff has the value") == "keywordNameCall"
    )


def test_variable_at_end_of_bdd_statement_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "The element WriteOff has the value ${value}", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("${") == "variableOperator"
    assert semantic_tokens.get("value") == "variable"
    assert semantic_tokens.get("}") == "variableOperator"


def test_tokens_identified_should_not_overlap(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "The element WriteOff has the value ${value}", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert not semantic_tokens.get("The element WriteOff has the value ${value}")


def test_variable_at_start_of_bdd_Statement_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "${message} has been sent within 5 seconds", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("${") == "variableOperator"
    assert semantic_tokens.get("message") == "variable"
    assert semantic_tokens.get("}") == "variableOperator"


def test_bdd_statement_following_variable_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "${message} has been sent within 5 seconds", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("has been sent within 5 seconds") == "keywordNameCall"
    assert not semantic_tokens.get("${message} has been sent within 5 seconds")


def test_variable_enclosed_in_square_brackets_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] an element with tag WriteOff exists",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert (
        semantic_tokens.get("In the section SupportingDocument[") == "keywordNameCall"
    )
    assert (
        semantic_tokens.get("] an element with tag WriteOff exists")
        == "keywordNameCall"
    )
    assert semantic_tokens.get("${") == "variableOperator"
    assert semantic_tokens.get("index") == "variable"
    assert semantic_tokens.get("}") == "variableOperator"
    assert not semantic_tokens.get(
        "In the section SupportingDocument[${index}] an element with tag WriteOff exists"
    )


def test_multiple_sequential_variables_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("index") == "variable"
    assert semantic_tokens.get("reference") == "variable"
    assert (
        semantic_tokens.get("In the section SupportingDocument[") == "keywordNameCall"
    )
    assert (
        semantic_tokens.get("] the element ID has been added with value")
        == "keywordNameCall"
    )
    assert not semantic_tokens.get(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}"
    )


def test_embedded_variable_opening_bracket_should_be_highlighted(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("${") == "variableOperator"


def test_embedded_variable_closing_bracket_should_be_highlighted(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("}") == "variableOperator"


def test_embedded_variable_should_be_highlighted(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("index") == "variable"


def test_embedded_variable_should_not_be_highlighted_in_single_color(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section SupportingDocument[${index}] the element ID has been added with value ${reference}",
        workspace,
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert not semantic_tokens.get("${index}")
