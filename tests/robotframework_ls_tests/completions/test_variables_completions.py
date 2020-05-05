def test_string_variables_completions(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
${NAME}         Robot Framework
${VERSION}      2.0
${ROBOT} =      ${NAME} ${VERSION}

*** Test Cases ***
List Variable
    Log    ${NAME}
    Should Contain    ${"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_list_variables_completions_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
@{NAMES}        Matti       Teppo
@{NAMES2}       @{NAMES}    Seppo

*** Test Cases ***
List Variable
    Log    @{NAMES}
    Should Contain    @{"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_list_variables_completions_in_variables(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
@{NAMES}        Matti       Teppo
@{NAMES2}       @{"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_dict_variables_completions(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
&{USER 1}       name=Matti    address=xxx         phone=123

*** Test Cases ***
List Variable
    Should Contain    &{"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_recursive(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """

*** Test Cases ***
List Variable
    Log    ${"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)
