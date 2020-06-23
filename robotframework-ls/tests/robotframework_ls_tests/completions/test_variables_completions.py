def test_string_variables_completions_basic_1(
    workspace, libspec_manager, data_regression
):
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
    Should Contain    ${N"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_string_variables_completions_basic_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Variables ***
${NAME}         Robot Framework
${VERSION}      2.0
${ROBOT}        ${n} ${VERSION}"""
    line, col = doc.get_last_line_col()
    completions = variable_completions.complete(
        CompletionContext(
            doc, workspace=workspace.ws, line=line, col=col - len("} ${VERSION}")
        )
    )
    data_regression.check(completions)


def test_string_variables_completions_unable_to_tokenize_1(
    workspace, libspec_manager, data_regression
):
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
    Should Contain    ${snth ${na}"""

    line, col = doc.get_last_line_col()
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - 2)
    )
    data_regression.check(completions)


def test_string_variables_completions_unable_to_tokenize_2(
    workspace, libspec_manager, data_regression
):
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
    Should Contain    ${na ${na}"""

    line, col = doc.get_last_line_col()
    completions = variable_completions.complete(
        CompletionContext(
            doc, workspace=workspace.ws, line=line, col=col - len(" ${na}")
        )
    )
    data_regression.check(completions)


def test_list_variables_completions_basic_1(
    workspace, libspec_manager, data_regression
):
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


def test_list_variables_completions_basic_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """*** Variables ***
@{NAMES}        Matti       Teppo

*** Test Cases ***
List Variable
    Should Contain    @{NA}"""
    line, col = doc.get_last_line_col()
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - 1)
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
    Log    ${VAR"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_1(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got ${variable"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got @{variable"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_3(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """
*** Test Cases ***
[SetUp]
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got @{variable"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_4(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """
*** Test Cases ***
[SetUp]
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    
Test1
    Log    We got @{variable"""

    # Note: local variables aren't available from one test to another.
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions, basename="no_variables")


def test_variables_completions_arguments_basic(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """
*** Keywords ***
This is the Test
    [Arguments]    ${arg}    ${arg2}
    Log To Console    ${ar"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_builtins(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """
*** Keywords ***
This is the Test
    [Arguments]    ${arg}    ${arg2}
    Log To Console    ${PREV_TEST_ST"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_in_resource_paths(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """
*** Variables ***
${SOME_DIR}         c:/foo/bar
    
*** Settings ***
Resource           ${some_d"""
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)
