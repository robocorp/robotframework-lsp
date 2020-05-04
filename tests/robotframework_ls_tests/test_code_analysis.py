def _collect_errors(workspace, doc, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_analysis import collect_analysis_errors

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]
    data_regression.check(errors)


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
