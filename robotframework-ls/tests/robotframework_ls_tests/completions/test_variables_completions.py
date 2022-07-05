import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_string_variables_completions_basic_1(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_string_variables_completions_basic_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_list_variables_completions_basic_1(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_list_variables_completions_basic_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_list_variables_completions_in_variables(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
@{NAMES}        Matti       Teppo
@{NAMES2}       @{"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards (OPTIONS completion only there).",
)
def test_dict_variables_completions(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """

*** Test Cases ***
List Variable
    Log    ${VAR""",
    )

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_1(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got ${variable""",
    )

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got @{variable""",
    )

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_3(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """
*** Test Cases ***
[SetUp]
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got @{variable""",
    )

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_assign_4(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """
*** Test Cases ***
[SetUp]
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    
Test1
    Log    We got @{variable""",
    )

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
    doc = workspace.put_doc("case4.robot")
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
    doc = workspace.put_doc("case4.robot")
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
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Variables ***
${SOME_DIR}         c:/foo/bar
    
*** Settings ***
Resource           ${some_d"""
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_in_variable_files(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_vars_file.robot")
    doc.source = """
*** Settings ***
Variables    ./robotvars.py


*** Test Cases ***
Test
    Log    ${VARIAB"""
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variables_completions_in_variable_files_yaml(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_vars_file.robot")
    doc.source = """
*** Settings ***
Variables    ./robotvars.yaml


*** Test Cases ***
Test
    Log    ${VARIAB"""
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_dictionary_variables_completions_with_dollar(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """*** Variables ***
&{ROBOT}   Name=Robot Framework   Version=4.0

***Test Cases***
Test dictionary variable completion
   Log to Console   ${ROB"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_dictionary_variables_completions_with_ampersand(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """*** Variables ***
&{ROBOT}   Name=Robot Framework   Version=4.0

***Test Cases***
Test dictionary variable completion
   Log to Console   &{ROB"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variable_completions_from_resource(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """*** Settings ***
Resource    case_vars_file_yml.resource


*** Test Cases ***
Test
    Log    ${VARIABLE_YAML_2}    console=True
    Log    ${Var|in.R"""

    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    data_regression.check(completions)


def test_variable_completions_empty(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import variable_completions

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """*** Keywords ***
Put Key
    ${ret}=    Create dictionary    key=${}"""

    line, col = doc.get_last_line_col()
    completions = variable_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - 1)
    )
    assert len(completions) > 10
    for completion in completions:
        assert completion["textEdit"]["range"]["end"]["character"] == col - 1


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards for WHILE.",
)
def test_variable_completions_in_expression(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """
*** Variables ***
${var a1}    ${1}

*** Test Cases ***
Test
    WHILE    $va"""

    completions = complete_all(CompletionContext(doc, workspace=workspace.ws))
    data_regression.check(completions)


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Requires RF 5 onwards for WHILE.",
)
def test_variable_completions_in_expression_1(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """
*** Variables ***
${var a1}    ${1}

*** Test Cases ***
Test
    WHILE    $"""

    line, col = doc.get_last_line_col()
    completions = complete_all(CompletionContext(doc, workspace=workspace.ws))
    assert len(completions) > 10
    found_var_a1 = False
    for completion in completions:
        assert completion["textEdit"]["range"]["end"]["character"] == col
        assert completion["textEdit"]["range"]["end"]["line"] == line
        if not found_var_a1:
            found_var_a1 = completion["label"] == "var_a1"

    assert found_var_a1


@pytest.mark.skipif(
    get_robot_major_version() < 5,
    reason="Completions differ on RF 3/4",
)
def test_variable_completions_in_assign(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """
*** Variables ***
${some var1}    1
${some var2}    2

*** Keywords ***
Put Key
    ${some }"""

    # In RF 3/4 the line with ${some } yields a Keyword call and in RF 5
    # it yields an EmptyLine, so, completions differ.

    line, col = doc.get_last_line_col()
    col -= 1
    completions = complete_all(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
    )
    data_regression.check(completions)


def test_variable_completions_in_no_builtins(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.server_api.server import complete_all

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_root.robot")
    doc.source = """
*** Variables ***
${some var1}    1
${some var2}    2

*** Keywords ***
Put Key
    ${e}"""

    # In RF 3/4 the line with ${some } yields a Keyword call and in RF 5
    # it yields an EmptyLine, so, completions differ.

    line, col = doc.get_last_line_col()
    col -= 1
    completions = complete_all(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
    )
    assert len(completions) == 2
