def test_semantic_highlighting_base(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

    workspace.set_root("case1")
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Settings ***
Library   my.lib

*** Keywords ***
Some Keyword
    [Arguments]     Some ${arg1}     Another ${arg2}
    Clear All Highlights    ${arg1}    ${arg2}
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    assert decode_semantic_tokens(semantic_tokens, doc) == [
        ("*** Settings ***", "header"),
        ("Library", "setting"),
        ("my.lib", "name"),
        ("*** Keywords ***", "header"),
        ("Some Keyword", "keywordNameDefinition"),
        ("[", "variableOperator"),
        ("Arguments", "setting"),
        ("]", "variableOperator"),
        ("Some ", "parameter"),
        ("${", "variableOperator"),
        ("arg1", "variable"),
        ("}", "variableOperator"),
        ("Another ", "parameter"),
        ("${", "variableOperator"),
        ("arg2", "variable"),
        ("}", "variableOperator"),
        ("Clear All Highlights", "keywordNameCall"),
        ("${", "variableOperator"),
        ("arg1", "variable"),
        ("}", "variableOperator"),
        ("${", "variableOperator"),
        ("arg2", "variable"),
        ("}", "variableOperator"),
    ]


def test_semantic_highlighting_keyword(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

    workspace.set_root("case1")
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Keywords ***
Some Keyword
    [Arguments]     ${arg1}
    Call Keyword    ${arg1}
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)
    semantic_tokens = semantic_tokens_full(context)
    assert decode_semantic_tokens(semantic_tokens, doc) == [
        ("*** Keywords ***", "header"),
        ("Some Keyword", "keywordNameDefinition"),
        ("[", "variableOperator"),
        ("Arguments", "setting"),
        ("]", "variableOperator"),
        ("${", "variableOperator"),
        ("arg1", "variable"),
        ("}", "variableOperator"),
        ("Call Keyword", "keywordNameCall"),
        ("${", "variableOperator"),
        ("arg1", "variable"),
        ("}", "variableOperator"),
    ]


def test_semantic_highlighting_for_if(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
    from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens

    workspace.set_root("case1")
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Keywords ***
Some keyword
    FOR    ${element}    IN       @{LIST}
        IF    ${random} == ${NUMBER_TO_PASS_ON}
            Pass Execution    "${random} == ${NUMBER_TO_PASS_ON}"
        ELSE IF    ${random} > ${NUMBER_TO_PASS_ON}
            Log To Console    Too high.
        ELSE
            Log To Console    Too low.
        END
    END
""".replace(
        "\r\n", "\n"
    ).replace(
        "\r", "\n"
    )
    context = CompletionContext(doc, workspace=workspace.ws)

    semantic_tokens = semantic_tokens_full(context)
    assert decode_semantic_tokens(semantic_tokens, doc) == [
        ("*** Keywords ***", "header"),
        ("Some keyword", "keywordNameDefinition"),
        ("FOR", "control"),
        ("${", "variableOperator"),
        ("element", "variable"),
        ("}", "variableOperator"),
        ("IN", "control"),
        ("@{", "variableOperator"),
        ("LIST", "variable"),
        ("}", "variableOperator"),
        ("IF", "control"),
        ("${", "variableOperator"),
        ("random", "variable"),
        ("}", "variableOperator"),
        (" == ", "parameter"),
        ("${", "variableOperator"),
        ("NUMBER_TO_PASS_ON", "variable"),
        ("}", "variableOperator"),
        ("Pass Execution", "keywordNameCall"),
        ('"', "parameter"),
        ("${", "variableOperator"),
        ("random", "variable"),
        ("}", "variableOperator"),
        (" == ", "parameter"),
        ("${", "variableOperator"),
        ("NUMBER_TO_PASS_ON", "variable"),
        ("}", "variableOperator"),
        ('"', "parameter"),
        ("ELSE IF", "control"),
        ("${", "variableOperator"),
        ("random", "variable"),
        ("}", "variableOperator"),
        (" > ", "parameter"),
        ("${", "variableOperator"),
        ("NUMBER_TO_PASS_ON", "variable"),
        ("}", "variableOperator"),
        ("Log To Console", "keywordNameCall"),
        ("Too high.", "parameter"),
        ("ELSE", "control"),
        ("Log To Console", "keywordNameCall"),
        ("Too low.", "parameter"),
        ("END", "control"),
        ("END", "control"),
    ]
