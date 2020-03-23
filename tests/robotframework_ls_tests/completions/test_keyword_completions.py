def test_keyword_completions_builtin(workspace, libspec_manager):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    should be"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    assert sorted([comp["label"] for comp in completions]) == [
        "Length Should Be",
        "Should Be Empty",
        "Should Be Equal",
        "Should Be Equal As Integers",
        "Should Be Equal As Numbers",
        "Should Be Equal As Strings",
        "Should Be True",
    ]


def test_keyword_completions_user(
    data_regression, workspace, tmpdir, cases, libspec_manager
):
    import os.path
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls_tests.fixtures import LIBSPEC_1

    workspace_dir = str(tmpdir.join("workspace"))
    cases.copy_to("case1", workspace_dir)

    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    verify"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_1")

    # Now, let's put a .libspec file in the workspace and check whether
    # it has priority over the auto-generated spec file.
    with open(os.path.join(workspace_dir, "new_spec.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.synchronize_workspace_folders()

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_2_new")
