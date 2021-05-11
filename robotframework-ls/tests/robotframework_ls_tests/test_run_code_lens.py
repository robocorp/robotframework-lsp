def test_run_code_lens_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """

*** Test Cases ***
Some Test
    [Documentation]      Docs
    
*** Task ***
Some Task
    [Documentation]      Docs
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens(completion_context)
    # For checking the test we need to make the uri the same among runs.
    for c in found:
        uri = c["command"]["arguments"][0]["uri"]
        c["command"]["arguments"][0]["uri"] = uri.split("/")[-1]
    data_regression.check(found)
