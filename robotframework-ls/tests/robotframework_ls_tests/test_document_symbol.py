def test_document_symbol(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.document_symbol import document_symbol

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """
    
*** Settings ***
Library    Foo
    
*** Test Cases ***
Some Test
    [Documentation]      Docs
    
*** Task ***
Some Task
    [Documentation]      Docs
    
Some Task 2
    [Documentation]      Docs
    
*** Keyword ***
Some Keyword
    [Documentation]      Docs
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = document_symbol(completion_context)
    data_regression.check(found)
