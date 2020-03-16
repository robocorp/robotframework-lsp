def test_keyword_completions_builtin(data_regression, workspace, tmpdir, cases):
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.libspec_manager import LibspecManager

    libspec_manager = LibspecManager(user_home=str(tmpdir.join("home")))
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


def test_keyword_completions_user(data_regression, workspace, tmpdir, cases):
    import os.path
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.libspec_manager import LibspecManager

    workspace_dir = str(tmpdir.join("workspace"))
    cases.copy_to("case1", workspace_dir)

    libspec_manager = LibspecManager(user_home=str(tmpdir.join("home")))
    workspace.set_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    verify"

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_1")

    # Now, let's put a .libspec file in the workspace and check whether
    # it has priority over the auto-generated spec file.
    new_contents = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case1_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case1_library``.</doc>
<kw name="new Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="New Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

    with open(os.path.join(workspace_dir, "new_spec.libspec"), "w") as stream:
        stream.write(new_contents)
    libspec_manager.synchronize()

    completions = keyword_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="keyword_completions_2_new")
