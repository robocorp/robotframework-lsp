import os


def check_code_action_data_regression(data_regression, found, basename=None):
    import copy

    # For checking the test we need to make the uri/path the same among runs.
    found = copy.deepcopy(found)  # we don't want to change the initial data
    for c in found:
        arguments = c["arguments"]
        if arguments:
            title = c["title"]
            if "(at " in title:
                c["title"] = title[: title.index("(at")]

            for c in arguments:
                label = c["apply_edit"]["label"]
                if "(at " in label:
                    c["apply_edit"]["label"] = label[: label.index("(at")]

                changes = c["apply_edit"]["edit"].get("changes", None)
                if changes:
                    new_changes = {}
                    for uri, v in changes.items():
                        uri = uri.split("/")[-1]
                        new_changes[uri] = v
                    c["apply_edit"]["edit"]["changes"] = new_changes

                changes = c["apply_edit"]["edit"].get("documentChanges", None)
                if changes:
                    for change in changes:
                        if change.get("kind") == "create":
                            change["uri"] = change["uri"].split("/")[-1]

                lint_uris = c.get("lint_uris")
                if lint_uris:
                    c["lint_uris"] = [os.path.basename(x) for x in lint_uris]

                show_document = c.get("show_document")
                if show_document:
                    show_document["uri"] = os.path.basename(show_document["uri"])

    data_regression.check(found, basename=basename)


def check_apply_result(doc, actions, expected):
    changes = next(
        iter(actions[0]["arguments"][0]["apply_edit"]["edit"]["changes"].values())
    )
    doc.apply_text_edits(changes)

    expected = expected.replace("\r\n", "\n").replace("\r", "\n")

    obtained = doc.source.replace("\r\n", "\n").replace("\r", "\n")
    if obtained != expected:
        print("Obtained:--")
        print(obtained)
        print("--")
        assert obtained == expected


def _collect_errors(completion_context):
    from robotframework_ls.impl.code_analysis import collect_analysis_errors

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]

    def key(diagnostic):
        return (
            diagnostic["range"]["start"]["line"],
            diagnostic["range"]["start"]["character"],
            diagnostic["message"],
        )

    errors = sorted(errors, key=key)
    return errors


def _analyze_and_create_completion_context(
    doc, workspace, kind="undefined_keyword", filter=False
):
    from robotframework_ls.impl.completion_context import CompletionContext

    errors = _collect_errors(CompletionContext(doc, workspace=workspace.ws))
    if filter:
        errors = [x for x in errors if x["data"] and x["data"]["kind"] == kind]

    assert len(errors) == 1
    error = next(iter(errors))

    diagnostic_data = error["data"]
    assert diagnostic_data["kind"] == kind

    end = error["range"]["end"]
    line = end["line"]
    col = end["character"]
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    return completion_context, diagnostic_data


def test_code_code_action_import_keyword_basic(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc_import_from = workspace.put_doc("import_from_this_robot.robot")
    doc_import_from.source = """
*** Keywords ***
My Keyword
    No Operation
    
My Keyword not shown
    No Operation
"""

    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Test Cases ***
Some Test
    [Documentation]      Docs
    My Keyword"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    actions = [x for x in actions if "Import My Keyword" in x["title"]]
    check_code_action_data_regression(data_regression, actions)
    check_apply_result(
        doc,
        actions,
        """*** Settings ***
Resource    import_from_this_robot.robot

*** Test Cases ***
Some Test
    [Documentation]      Docs
    My Keyword""",
    )


def test_code_code_action_create_keyword_same_file(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Test Cases ***
Some Test
    My Keyword"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)
    check_apply_result(
        doc,
        actions,
        """
*** Keywords ***
My Keyword

*** Test Cases ***
Some Test
    My Keyword""",
    )


def test_code_code_action_create_keyword_existing_section_same_file(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Something
    No Operation

Sample
    No operation
    
    
*** Test Cases ***
Some Test
    My Keyword"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)
    check_apply_result(
        doc,
        actions,
        """
*** keywords ***
Something
    No Operation

Sample
    No operation
    
    
My Keyword

*** Test Cases ***
Some Test
    My Keyword""",
    )


def test_code_code_action_create_keyword_current_section(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Something
    No operation

Sample
    No operation
    
    My Keyword
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)
    check_apply_result(
        doc,
        actions,
        """
*** keywords ***
Something
    No operation

My Keyword

Sample
    No operation
    
    My Keyword
""",
    )


def test_code_code_action_create_keyword_with_args(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Something
    No operation

    Run Keyword     Foobar    value    another=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)

    check_apply_result(
        doc,
        actions,
        """
*** keywords ***
Foobar
    [Arguments]    ${value}    ${another}


Something
    No operation

    Run Keyword     Foobar    value    another=10
""",
    )


def test_code_code_action_create_resource(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Resource    ./import_from_this_robot.robot
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "undefined_resource"
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)


def test_code_code_action_create_library(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Library    .${/}import_from_this_lib.py
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "undefined_library"
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)


def test_code_code_action_create_variables(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Variables    ${CURDIR}/my_vars.py
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "undefined_var_import"
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)


def test_code_code_action_create_keyword_in_another_file(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc_target = workspace.put_doc("my_resource.resource")

    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Resource    ./my_resource.resource

*** Test Case ***
My Test
    my_resource.Foobar    arg=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, filter=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)

    check_apply_result(
        doc_target,
        actions,
        """*** Keywords ***
Foobar
    [Arguments]    ${arg}


""",
    )


def test_code_code_action_create_keyword_in_another_file_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc_target = workspace.put_doc("my_resource.resource")
    doc_target.source = """*** Keywords ***
My test
    Log     Something"""

    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Resource    ./my_resource.resource

*** Test Case ***
My Test
    my_resource.Foobar    arg=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, filter=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    # check_code_action_data_regression(data_regression, actions)

    check_apply_result(
        doc_target,
        actions,
        """*** Keywords ***
My test
    Log     Something

Foobar
    [Arguments]    ${arg}


""",
    )


def test_code_code_action_create_keyword_in_another_file_3(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc_target = workspace.put_doc("my_resource.resource")
    doc_target.source = """*** Keywords ***
My test
    Log     Something
"""

    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Resource    ./my_resource.resource

*** Test Case ***
My Test
    my_resource.Foobar    arg=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, filter=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    # check_code_action_data_regression(data_regression, actions)

    check_apply_result(
        doc_target,
        actions,
        """*** Keywords ***
My test
    Log     Something


Foobar
    [Arguments]    ${arg}


""",
    )
