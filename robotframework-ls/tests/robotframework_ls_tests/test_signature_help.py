def test_signature_help_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help
    from robocorp_ls_core.lsp import MarkupKind

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Log It
    Log    """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = signature_help(completion_context)
    signatures = result["signatures"]

    # Don't check the signature documentation in the data regression so that the
    # test doesn't become brittle.
    docs = signatures[0].pop("documentation")
    assert sorted(docs.keys()) == ["kind", "value"]
    assert docs["kind"] == MarkupKind.Markdown
    assert "Log" in docs["value"]
    data_regression.check(result)
