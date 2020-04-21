def test_find_definition_builtin(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    Should Be Empty"

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("BuiltIn.py")
    assert definition.lineno > 0


def test_find_definition_keyword(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")

    for i in range(4, 10):
        completion_context = CompletionContext(
            doc, workspace=workspace.ws, line=7, col=i
        )
        definitions = find_definition(completion_context)
        assert len(definitions) == 1, "Failed to find definitions for col: %s" % (i,)
        definition = next(iter(definitions))
        assert definition.source.endswith("case2.robot")
        assert definition.lineno == 1
