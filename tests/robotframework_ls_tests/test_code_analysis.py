def _collect_errors(workspace, doc, data_regression, basename=None, config=None):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_analysis import collect_analysis_errors

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]
    data_regression.check(errors, basename=basename)


def test_keywords_analyzed(workspace, libspec_manager, data_regression):

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + (
        "\n    This keyword does not exist" "\n    [Teardown]    Also not there"
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_analyzed_templates(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Settings ***
Test Template    this is not there"""

    _collect_errors(workspace, doc, data_regression)


def test_keywords_with_vars_no_error(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = (
        doc.source
        + """
    I check ls
    I execute "ls" rara "-lh"

*** Keywords ***
I check ${cmd}
    Log    ${cmd}

I execute "${cmd}" rara "${opts}"
    Log    ${cmd} ${opts}
    
"""
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_with_prefix_no_error(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    # Ignore bdd-related prefixes (see: robotframework_ls.impl.robot_constants.BDD_PREFIXES)
    doc.source = (
        doc.source
        + """
    given I check ls
    then I execute

*** Keywords ***
I check ${cmd}
    Log    ${cmd}

I execute
    Log    foo
"""
    )

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keywords_prefixed_by_library(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")

    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    BuiltIn.Log    Logging
    case4resource3.Yet Another Equal Redefined
    String.Should Be Titlecase    Hello World
    ${list}=    BuiltIn.Create List    1    2
    Collections.Append To List    ${list}    3"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_resource_does_not_exist(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")

    doc.source = """*** Settings ***
Library    DoesNotExist
Library    .
Library    ..
Library    ../
Resource    does_not_exist.txt
Resource    ${foo}/does_not_exist.txt
Resource    ../does_not_exist.txt
Resource    .
Resource    ..
Resource    ../
Resource    ../../does_not_exist.txt
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3.Yet Another Equal Redefined"""

    from robotframework_ls.config.config import Config

    config = Config(root_uri="", init_opts={}, process_id=-1, capabilities={})
    # Note: we don't give errors if we can't resolve a resource.
    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)
