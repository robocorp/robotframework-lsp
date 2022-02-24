from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

robot_framework_template_file ="""
*** Settings ***
Library   my.lib
                    
*** Test Cases ***
Foobar
    <PLACEHOLDER_TESTCASE_KEYWORD>
    REQUESTS.Call from Requests library

*** Keywords ***
Some Keyword
    [Arguments]     Some ${arg1}     Another ${arg2}
    Clear All Highlights    ${arg1}    ${arg2}
    <PLACEHOLDER_KEYWORDS_KEYWORD>
    FOR    ${i}    IN RANGE    1000
        ${found_cards}=    Get card names
        Append to list    ${cards}    @{found_cards}
        ${is_end_of_page}=    Check if we are at end of page
        Exit For Loop If     ${is_end_of_page}==${TRUE}
        Scroll to next part of page        
    END
""".replace("\r\n", "\n").replace("\r", "\n")

def set_test_case_with_keyword(keyword, workspace):
    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    robot_framework_source_file = robot_framework_template_file.replace("<PLACEHOLDER_TESTCASE_KEYWORD>", keyword)
    doc.source = robot_framework_source_file
    return doc

def set_keyword_in_keyword_section(keyword, workspace):
    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    robot_framework_source_file = robot_framework_template_file.replace("<PLACEHOLDER_KEYWORDS_KEYWORD>", keyword)
    doc.source = robot_framework_source_file
    return doc

def get_semantic_tokens_from_language_server(workspace, doc):
    from robotframework_ls.impl.completion_context import CompletionContext
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

def test_gherkin_at_beginning_of_keyword_should_be_highlighed(workspace):
    robot_source_file = set_test_case_with_keyword("Given Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    print(semantic_tokens)
    assert semantic_tokens.get("Given") == "control"
    assert semantic_tokens.get("Some BDD description of desired system behaviour") == "keywordNameCall"
    assert not semantic_tokens.get("Given Some BDD description of desired system behaviour")

def test_gherkin_when_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("When Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("When") == "control"

def test_gherkin_then_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("Then Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("Then") == "control"

def test_gherkin_and_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("And Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("And") == "control"

def test_gherkin_but_should_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("But Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("But") == "control"

def test_gherkin_recognition_should_be_case_insensitive(workspace):
    robot_source_file = set_test_case_with_keyword("givEN Some BDD description of desired system behaviour", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("givEN") == "control"

def test_false_gherkin_in_middle_of_keyword_should_not_be_highlighted(workspace):
    robot_source_file = set_test_case_with_keyword("Then The system under test has given something", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("The system under test has given something") == "keywordNameCall"
    assert not semantic_tokens.get("given")

def test_gherkin_in_keyword_sections_should_also_be_highlighted(workspace):
    robot_source_file = set_keyword_in_keyword_section("Then The system under test has given something", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("Then") == "control"

def test_library_prefix_should_be_highlighted(workspace):
    robot_source_file = set_keyword_in_keyword_section("Requests.GET    url=https://github.com/robocorp/robotframework-lsp/issues/581", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("Requests") == "name"
    assert semantic_tokens.get("GET") == "keywordNameCall"
    
def test_module_prefix_abuse_in_bdd_should_be_supported(workspace):
    robot_source_file = set_test_case_with_keyword("Given Module.Keyword    With parameter", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("Given") == "control"
    assert semantic_tokens.get("Module") == "name"
    assert semantic_tokens.get("Keyword") == "keywordNameCall"

def test_keywords_should_not_be_mistaken_for_gherkin(workspace):
    robot_source_file = set_test_case_with_keyword("Buttercup    ${argument_1}    ${argument_2}", workspace)
    semantic_tokens = get_semantic_tokens_from_language_server(workspace, robot_source_file)
    assert semantic_tokens.get("Buttercup") == "keywordNameCall"
    assert not semantic_tokens.get("But")
