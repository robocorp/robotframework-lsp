from robotframework_ls.impl.completion_context import CompletionContext
from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

robot_framework_template_file = """
** Settings ***

Test Teardown    
Resource    ${EXECDIR}/resources/Gherkin/Given/Declaration.resource
Resource    ${EXECDIR}/resources/Gherkin/Given/Sections.resource
Resource    ${EXECDIR}/resources/Gherkin/When/When.robot
Resource    ${EXECDIR}/resources/Gherkin/Then/Messages.resource

resource    ${CURDIR}/shared.resource

Force Tags    SKIP

*** Test Cases ***

Multiple licenses in a single article
    Given A UM-MIG compliant B1 declaration with all mandatory elements
    And In the section Destination the element CountryCode has the value AL
    And Licence is specified with type C068 reference NL0074CDIU0571970 amount 1 and currency EUR
    And Licence is specified with type C068 reference NL0074CDIU0571971 amount 1 and currency EUR
    And In the section SupportingDocument[2] the element WriteOff has been removed
    And In the section Classification the element ID has the value 30049000
    When The declaration is submitted to DMS
    And The declaration processing status is 2 or higher
    Then Message DVV02: Validate Customer Licence should be sent exactly 2 times


*** Keywords ***
  
Licence is specified with type ${type} reference ${reference} amount ${amount} and currency ${currency}
    ${index}=    Get sequence numeric for new SupportingDocument element in section GovernmentAgencyGoodsItem
    In the section GovernmentAgencyGoodsItem an element with tag SupportingDocument has been added
    In the section SupportingDocument[${index}] the element ID has been added with value ${reference}
    In the section SupportingDocument[${index}] the element TypeCode has been added with value ${type}
    In the section SupportingDocument[${index}] the element SequenceNumeric has been added with value ${index}
    In the section SupportingDocument[${index}] an element with tag WriteOff exists
    In the section SupportingDocument[${index}]/WriteOff the element AmountAmount has been added with value ${amount}
    In the section SupportingDocument[${index}]/WriteOff the element AmountAmount has attribute currencyID with value ${currency}
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
    return grammar_token_mapping


def test_variable_at_end_of_bdd_statement_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "The element WriteOff has the value ${value}", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert (
        semantic_tokens.get("The element WriteOff has the value") == "keywordNameCall"
    )
    assert semantic_tokens.get("${value}") == "variable"
    assert not semantic_tokens.get("The element WriteOff has the value ${value}")


def test_variable_embedded_in_bdd_statement_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "In the section ${section} an element with tag WriteOff exists", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("In the section") == "keywordNameCall"
    assert (
        semantic_tokens.get("an element with tag WriteOff exists") == "keywordNameCall"
    )
    assert semantic_tokens.get("${section}") == "variable"
    assert not semantic_tokens.get(
        "In the section ${section} an element with tag WriteOff exists"
    )


def test_variable_at_start_of_bdd_Statement_should_be_recognized(workspace):
    robot_source_file = set_keyword_in_keyword_section(
        "${message} has been sent within 5 seconds", workspace
    )
    semantic_tokens = get_semantic_tokens_from_language_server(
        workspace, robot_source_file
    )
    assert semantic_tokens.get("${message}") == "variable"
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
    assert semantic_tokens.get("${index}") == "variable"
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
    assert semantic_tokens.get("${index}") == "variable"
    assert semantic_tokens.get("${reference}") == "variable"
    assert (
        semantic_tokens.get("In the section SupportingDocument[") == "keywordNameCall"
    )
    assert (
        semantic_tokens.get("] the element ID has been added with value ")
        == "keywordNameCall"
    )
    assert not semantic_tokens.get(
        "In the section SupportingDocument[${index}] an element with tag WriteOff exists"
    )
