def test_folding_range_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.folding_range import folding_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Log   
    Log   
    
Log It 2
    Log   
    Log   
Log It 3
    Log   
    Log 
    FOR    ${element}    IN    @{LIST}
        Log    ${element}
        
    END
Nothing here  
""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    data_regression.check(folding_range(completion_context))
