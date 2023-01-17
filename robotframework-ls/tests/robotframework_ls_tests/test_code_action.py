import os
from robotframework_ls.impl.protocols import IRobotDocument
from robocorp_ls_core.lsp import Range
from typing import Set


def check_code_action_data_regression(data_regression, found, basename=None):
    import copy

    # For checking the test we need to make the uri/path the same among runs.
    found = copy.deepcopy(found)  # we don't want to change the initial data
    for code_action in found:
        title = code_action["title"]
        if "(at " in title:
            code_action["title"] = title[: title.index("(at")]

        c = code_action["command"]
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


def check_apply_result(doc, actions, expected, title=None):
    if title is not None:
        actions = [x for x in actions if x["title"] == title]

    assert len(actions) == 1
    arguments = actions[0]["command"]["arguments"]
    assert len(arguments) == 1
    argument_opts = arguments[0]
    if "apply_edit" in argument_opts:
        changes = next(iter(argument_opts["apply_edit"]["edit"]["changes"].values()))
    else:
        changes = next(iter(argument_opts["apply_snippet"]["edit"]["changes"].values()))
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
    doc, workspace, kind="undefined_keyword", filter_kind=False
):
    from robotframework_ls.impl.completion_context import CompletionContext

    errors = _collect_errors(CompletionContext(doc, workspace=workspace.ws))
    if filter_kind:
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


def test_code_code_action_use_template(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.code_action import code_action
    from robotframework_ls.robot_config import RobotConfig

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

    config = RobotConfig()
    config.update(
        {
            "robot": {
                "quickFix.keywordTemplate": "$keyword_name$keyword_arguments\n    [Documentation]    Add docs for $keyword_name\n    $cursor\n",
            }
        }
    )
    completion_context = completion_context.create_copy_with_config(config)
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)
    check_apply_result(
        doc,
        actions,
        """
*** Keywords ***
My Keyword
    [Documentation]    Add docs for My Keyword
    
*** Test Cases ***
Some Test
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


def test_code_code_action_add_arg_after_existing_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Foobar
    [Arguments]    ${foo}
    No Operation
    
Something
    Foobar    1    another=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "unexpected_argument"
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
    [Arguments]    ${foo}    ${another}
    No Operation
    
Something
    Foobar    1    another=10
""",
    )


def test_code_code_action_add_with_no_existing_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Foobar
    [Arguments]
    No Operation
    
Something
    Foobar    another=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "unexpected_argument"
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
    [Arguments]    ${another}
    No Operation
    
Something
    Foobar    another=10
""",
    )


def test_code_code_action_add_with_no_existing_arg_section(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Foobar
    No Operation
    
Something
    Foobar    another=10
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "unexpected_argument"
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
    [Arguments]    ${another}
    No Operation
    
Something
    Foobar    another=10
""",
    )


def test_code_code_action_add_2nd_named_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** keywords ***
Foobar
    [Arguments]    ${a}
    No Operation
    
Something
    Foobar    a=10    b=20
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "unexpected_argument"
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
    [Arguments]    ${a}    ${b}
    No Operation
    
Something
    Foobar    a=10    b=20
""",
    )


def test_code_code_action_in_another_file(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc_import = workspace.put_doc("import_from.robot")
    doc_import.source = """
*** keywords ***
Foobar
    [Arguments]    ${a}
    No Operation
"""

    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Settings ***
Resource    import_from.robot

*** Test Cases ***
Something
    Foobar    a=10    b=20
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, "unexpected_argument"
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)
    check_code_action_data_regression(data_regression, actions)

    check_apply_result(
        doc_import,
        actions,
        """
*** keywords ***
Foobar
    [Arguments]    ${a}    ${b}
    No Operation
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
        doc, workspace, filter_kind=True
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
        doc, workspace, filter_kind=True
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
        doc, workspace, filter_kind=True
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


def test_code_code_action_create_local_variable(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Keywords ***
My keyword
    Log     Something ${myvar}
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Keywords ***
My keyword
    ${myvar}=    Set Variable    
    Log     Something ${myvar}
""",
        title="Create local variable",
    )


def test_code_code_action_create_local_variable_with_indent(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Tasks ***
Example task
    IF    $True
        Log    ${some_var}
    END
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Tasks ***
Example task
    IF    $True
        ${some_var}=    Set Variable    
        Log    ${some_var}
    END
""",
        title="Create local variable",
    )


def test_code_code_action_create_local_variable_continuation(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Tasks ***
Example task
    Log
        ...    ${some_var}
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Tasks ***
Example task
    ${some_var}=    Set Variable    
    Log
        ...    ${some_var}
""",
        title="Create local variable",
    )


def test_code_code_action_create_variable_in_section(workspace, libspec_manager):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Tasks ***
Example task
    Log    ${some_var}
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Variables ***
${some_var}    

*** Tasks ***
Example task
    Log    ${some_var}
""",
        title="Create variable in variables section",
    )


def test_code_code_action_create_variable_in_existing_section(
    workspace, libspec_manager
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Variables ***
${vv}    22

*** Tasks ***
Example task
    Log    ${some_var}
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Variables ***
${vv}    22
${some_var}    

*** Tasks ***
Example task
    Log    ${some_var}
""",
        title="Create variable in variables section",
    )


def test_code_code_action_create_variable_in_existing_section_2(
    workspace, libspec_manager
):
    from robotframework_ls.impl.code_action import code_action

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("my_robot.robot")
    doc.source = """*** Variables ***

*** Tasks ***
Example task
    Log    ${some_var}
"""

    completion_context, diagnostic_data = _analyze_and_create_completion_context(
        doc, workspace, kind="undefined_variable", filter_kind=True
    )
    found_data = [diagnostic_data]
    actions = code_action(completion_context, found_data)

    check_apply_result(
        doc,
        actions,
        """*** Variables ***
${some_var}    

*** Tasks ***
Example task
    Log    ${some_var}
""",
        title="Create variable in variables section",
    )


def _code_action_refactoring(
    workspace, libspec_manager, only: Set[str], initial_source, expected
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_action_refactoring import code_action_refactoring

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc: IRobotDocument = workspace.put_doc("my_robot.robot")
    i = initial_source.find("|")
    j = initial_source.find("|", i + 1)
    assert i > 0
    assert j > i

    source = initial_source[0:i] + initial_source[i + 1 : j] + initial_source[j + 1 :]
    doc.source = source

    start = doc.offset_to_line_col(i)
    end = doc.offset_to_line_col(j - 1)
    select_range = Range(start, end)

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=start[0], col=start[1]
    )

    actions = list(code_action_refactoring(completion_context, select_range, only))

    check_apply_result(doc, actions, expected)


def test_code_code_action_refactoring_extract_local_basic(workspace, libspec_manager):
    _code_action_refactoring(
        workspace,
        libspec_manager,
        "refactor.extract.local",
        """*** Tasks ***
Example task
    Log    some |value|
""",
        """*** Tasks ***
Example task
    ${${0:variable}}=    Set Variable    value
    Log    some ${${0:variable}}
""",
    )


def test_code_code_action_refactoring_extract_local_multiline(
    workspace, libspec_manager
):
    _code_action_refactoring(
        workspace,
        libspec_manager,
        "refactor.extract.local",
        """*** Tasks ***
Example task
    Log
        ...    |value|
""",
        """*** Tasks ***
Example task
    ${${0:variable}}=    Set Variable    value
    Log
        ...    ${${0:variable}}
""",
    )
