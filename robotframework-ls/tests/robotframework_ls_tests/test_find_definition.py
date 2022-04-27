from typing import Tuple
import os.path
import pytest
from robotframework_ls.impl.robot_version import get_robot_major_version


def test_find_definition_builtin(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc("case1.robot", doc.source + "\n    Should Be Empty")

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


def test_find_definition_keyword_resource_in_pythonpath(
    workspace, libspec_manager, cases
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    case2_path = cases.get_path("case2")
    config = RobotConfig()
    config.update({"robot": {"pythonpath": [case2_path]}})
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [case2_path]
    libspec_manager.config = config

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """
*** Settings ***
Resource    case2.robot"""

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1, "Failed to find definition"
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 0


def test_find_definition_keyword_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot", doc.source + "\n    [Teardown]    my_Equal redefined"
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 1


def test_find_definition_keyword_settings_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot", doc.source + "\n*** Keywords ***\nTeardown    my_Equal redefined"
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 1


def test_find_definition_keyword_test_template_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Settings ***
Test Template    my equal_redefined"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 2


def test_find_definition_keyword_embedded_args(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
I check ${cmd}
    Log    ${cmd}
    
*** Test Cases ***
Test 1
    I check ls"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 2


def test_find_definition_keyword_prefix(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
I check ${cmd}
    Log    ${cmd}
    
*** Test Cases ***
Test 1
    when I check ls"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 2


def test_find_definition_keyword_prefix2(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
I check ${cmd}
    Log    ${cmd}
    
*** Test Cases ***
Test 1
    when icheck ls"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 2


def test_find_definition_library_prefix(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3.Yet Another Equal Redefined"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case4resource3.robot")
    assert definition.lineno == 1


def test_find_definition_library_prefix_builtin(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc("case4.robot", doc.source + "\n    BuiltIn.Should Be Empty")

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("BuiltIn.py")
    assert definition.lineno > 0


def test_find_definition_library_prefix_with_name(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """*** Settings ***
Library    Collections    WITH NAME    col 1

*** Test Cases ***
Test
    Col1.Append To List    ${list}    3"""

    line, col = doc.get_last_line_col()
    col -= len(" List    ${list}    3")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("Collections.py")
    assert definition.lineno > 0


def test_find_definition_library_itself(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """*** Settings ***
Library    Collections"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("Collections.py")


def test_find_definition_resource_itself(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """*** Settings ***

Resource    case4resource.txt"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case4resource.txt")


def test_find_definition_variables_file_yaml(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_file_yaml.robot")
    line_contents = "Variables    ./robotvars.yaml"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 1
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("robotvars.yaml")


def test_find_definition_variables_file_yaml_from_resource(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_root.robot")
    line_contents = "    Log    ${VARIABLE_YAML_2}    console=True"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=18
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("robotvars.yml")
    assert definition.lineno == 1
    assert definition.col_offset == 0


def test_find_definition_variables_from_resource(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_root.robot")
    line_contents = "    Log    ${Var|in.Resource}    console=True"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=18
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case_vars_file_yml.resource")
    assert definition.lineno == 5


def test_find_definition_variables_file_py(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_file.robot")
    line_contents = "Variables    ./robotvars.py"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 1
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("robotvars.py")


@pytest.mark.parametrize(
    "line_and_basename",
    [
        ("    Log To Console    ${GLOBAL_VAR}", "__init__.robot"),
        ("    Log To Console    ${CONST_1}", "my.robot"),
    ],
)
def test_find_definition_set_vars_global(workspace, libspec_manager, line_and_basename):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_global_vars", libspec_manager=libspec_manager)
    doc = workspace.get_doc("my.robot")
    line_contents, basename = line_and_basename
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=len(line_contents) - 3
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith(basename)


def test_find_definition_variable_from_variables_file_yaml(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_file_yaml.robot")
    line_contents = "    Log    ${VARIABLE_YAML_2}    console=True"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=18
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("robotvars.yaml")
    assert definition.lineno == 1
    assert definition.col_offset == 0


def test_find_definition_variable_from_variables_file_py(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_file.robot")
    line_contents = "    Log    ${VARIABLE_1}    console=True"
    line = doc.find_line_with_contents(line_contents)
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=18
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("robotvars.py")
    assert definition.lineno == 0
    assert definition.col_offset == 0


def _definitions_to_data_regression(definitions):
    """
    :param IDefinition definition:
    """
    from os.path import os

    return [
        {
            "source": os.path.basename(definition.source),
            "lineno": definition.lineno,
            "end_lineno": definition.end_lineno,
            "col_offset": definition.col_offset,
            "end_col_offset": definition.end_col_offset,
        }
        for definition in definitions
    ]


def test_find_definition_variables_assign(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc = workspace.put_doc(
        "case4.robot",
        doc.source
        + """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got ${variable_x}""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_in_section(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Variables ***
${SOME_DIR}         c:/foo/bar
    
*** Settings ***
Resource           ${some dir}"""
    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_builtins(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Keywords ***
This is the Test
    [Arguments]    ${arg}    ${arg2}
    Log To Console    ${PREV_TEST_STATUS}"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_arguments(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Keywords ***
This is the Test
    [Arguments]    ${arg}    ${arg2}
    Log To Console    arg=${arg2}"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_list(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Variables ***
@{SOME LIST}    foo    bar    baz
&{SOME DICT}    string=cat    int=${1}    list=@{SOME LIST}


*** Test Cases ***
Log Global Constants
    Log    ${SOME LIST}    info"""

    line, col = doc.get_last_line_col()
    col -= len("ST}    info")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_dict(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Variables ***
@{SOME LIST}    foo    bar    baz
&{SOME DICT}    string=cat    int=${1}    list=@{SOME LIST}


*** Test Cases ***
Log Global Constants
    Log    ${SOME LIST}    info
    Log    ${SOME DICT}    info"""

    line, col = doc.get_last_line_col()
    col -= len("CT}    info")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_variables_dict_access(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """
*** Variables ***
&{Person}   First name=John   Last name=Smith

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[First]"""

    line, col = doc.get_last_line_col()
    col -= len("n}[First]")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_find_definition_curdir(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_curdir", libspec_manager=libspec_manager)
    doc = workspace.get_doc("main.robot")

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_variables_completions_recursive(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc = workspace.put_doc(
        "case5.robot",
        doc.source
        + """

*** Test Cases ***
List Variable
    Log    ${VAR2}""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def create_case_as_link(cases, tmpdir, case_name) -> Tuple[str, str]:
    target_original = cases.get_path(case_name)
    import os

    target_link = str(tmpdir.join(case_name))
    os.symlink(target_original, target_link, target_is_directory=True)
    return target_original, target_link


def check_using_link_version(
    found_at_source: str, target_link: str, target_original: str
):
    from pathlib import Path

    path = Path(found_at_source)
    found_parent = str(path.parent).lower()
    symlinked_version = target_link.lower()
    non_symlinked_version = str(target_original).lower()

    assert symlinked_version != non_symlinked_version
    assert found_parent != non_symlinked_version
    assert found_parent == symlinked_version


def test_find_definition_should_not_resolve_link_in_curr_file(
    workspace, libspec_manager, tmpdir, cases
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    target_original, target_link = create_case_as_link(cases, tmpdir, "case2")
    workspace.set_absolute_path_root(target_link, libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")

    col = 4
    completion_context = CompletionContext(doc, workspace=workspace.ws, line=7, col=4)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1, "Failed to find definitions for col: %s" % (col,)
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 1
    check_using_link_version(definition.source, target_link, target_original)


def test_find_definition_should_not_resolve_link_in_resource(
    workspace, libspec_manager, cases, tmpdir
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    target_original, target_link = create_case_as_link(cases, tmpdir, "case4")
    workspace.set_absolute_path_root(target_link, libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")
    doc.source = """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3.Yet Another Equal Redefined"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case4resource3.robot")
    assert definition.lineno == 1
    check_using_link_version(definition.source, target_link, target_original)


def test_find_definition_same_basename(workspace, libspec_manager, cases, tmpdir):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_same_basename", libspec_manager=libspec_manager)
    doc1 = workspace.get_doc("tasks1.robot")
    doc2 = workspace.get_doc("directory/tasks2.robot")

    completion_context = CompletionContext(doc1, workspace=workspace.ws)
    def1 = find_definition(completion_context)

    completion_context = CompletionContext(doc2, workspace=workspace.ws)
    def2 = find_definition(completion_context)
    assert len(def1) == 1
    assert len(def2) == 1
    assert (
        def1[0].source.replace("\\", "/").endswith("case_same_basename/my_library.py")
    )
    assert (
        def2[0]
        .source.replace("\\", "/")
        .endswith("case_same_basename/directory/my_library.py")
    )

    found = [
        lib_info
        for lib_info in libspec_manager.iter_lib_info()
        if lib_info.library_doc.name == "my_library"
    ]

    assert len(found) == 2


def test_find_definition_in_package_init(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_package_lib", libspec_manager=libspec_manager)
    doc1 = workspace.get_doc("case_package.robot")

    completion_context = CompletionContext(doc1, workspace=workspace.ws)
    def1 = find_definition(completion_context)
    assert len(def1) == 1
    assert def1[0].source.endswith("__init__.py")
    assert os.path.basename(os.path.dirname(def1[0].source)) == "package"


def test_find_definition_in_pythonpath(workspace, libspec_manager, cases):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    add_to_pythonpath = cases.get_path("case_search_pythonpath/libraries")
    config = RobotConfig()
    config.update({"robot": {"pythonpath": [add_to_pythonpath]}})
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [add_to_pythonpath]
    libspec_manager.config = config

    workspace.set_root("case_search_pythonpath", libspec_manager=libspec_manager)
    doc1 = workspace.get_doc("case_search_pythonpath.robot")

    completion_context = CompletionContext(doc1, workspace=workspace.ws, config=config)
    def1 = find_definition(completion_context)
    assert len(def1) == 1
    assert def1[0].source.endswith("lib_in_pythonpath.py")


def test_find_definition_resource_in_pythonpath(workspace, libspec_manager, cases):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition
    import sys

    add_to_pythonpath = cases.get_path("case_search_pythonpath_resource/resources")
    sys.path.append(add_to_pythonpath)

    try:
        workspace.set_root(
            "case_search_pythonpath_resource", libspec_manager=libspec_manager
        )
        doc1 = workspace.get_doc("case_search_pythonpath.robot")

        completion_context = CompletionContext(doc1, workspace=workspace.ws)
        def1 = find_definition(completion_context)
        assert len(def1) == 1
        assert def1[0].source.endswith("resource_in_pythonpath.robot")
    finally:
        sys.path.remove(add_to_pythonpath)


def test_find_definition_on_keyword_argument(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot", doc.source + "\n    Run Keyword If    ${var}    Should Be Empty"
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("BuiltIn.py")
    assert definition.lineno > 0


def test_find_definition_on_keyword_argument_variable(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
        doc.source
        + (
            "\n    ${variable_x} =    Get Some Variable"
            "\n    Run Keyword If    ${var}    ${variable_x}"
        ),
    )

    line, col = doc.get_last_line_col()
    col -= 1
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case1.robot")
    assert definition.lineno == line - 1


def test_find_definition_on_template_keyword(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
    doc.source = """
*** Keyword ***
Example Keyword

*** Test Cases **
Normal test case
    Example keyword    first argument    second argument

Templated test case
    [Template]    Example keyword
    first argument    second argument
"""

    line, col = doc.get_last_line_col_with_contents("[Template]    Example keyword")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case1.robot")
    assert definition.lineno == 2


@pytest.mark.parametrize(
    "server_port",
    [
        8270,
        0,
    ],
)
def test_find_definition_remote_library(workspace, libspec_manager, remote_library):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case_remote_library", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_remote.robot")
    port = remote_library
    doc = workspace.put_doc(
        "case_remote.robot",
        doc.source.replace("${PORT}", str(port))
        + "\n    a.Verify That Remote is Running",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("Remote.py")
    assert definition.lineno == -2


def test_var_from_for(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    FOR  ${vv}  IN  ${{[1, 2, 3]}}
        Log    ${vv}
    END
"""

    line, col = doc.get_last_line_col_with_contents("Log    ${vv}")
    col -= 1
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 3


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_var_from_except(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    TRY
        Log  something
    EXCEPT    AS    ${ee}
        Log    ${ee}
    END
"""

    line, col = doc.get_last_line_col_with_contents("Log    ${ee}")
    col -= 1
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 5


def test_var_in_outer_scope(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    ${aa}=    Set Variable    33
    FOR  ${ii}  IN  ${{[1, 2, 3]}}
        Log    ${aa}
    END
"""

    line, col = doc.get_last_line_col_with_contents("Log    ${aa}")
    col -= 1
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 3


def test_find_var_in_expression(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    ${aa}=    Set Variable    33
    Log    ${{$aa}}
"""

    line, col = doc.get_last_line_col_with_contents("Log    ${{$aa}}")
    col -= 2
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 3


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_find_var_in_expression_2(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${var_a}    ${1}

*** Test Cases ***
Test
    WHILE    $var_a < 2
        Log    ${var_a}
        ${var_a}=    Evaluate    $var_a + 1
    END
"""

    line, col = doc.get_last_line_col_with_contents("WHILE    $var_a < 2")
    col -= len("r_a < 2")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1  # The global is found.
    for definition in definitions:
        assert definition.source.endswith("case2.robot")
        assert definition.lineno == 2

    # Now, check directly at the ${var_a}=
    line, col = doc.get_last_line_col_with_contents(
        "        ${var_a}=    Evaluate    $var_a + 1"
    )
    col -= len("a}=    Evaluate    $var_a + 1")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 2  # Both declarations are found.
    for definition in definitions:
        assert definition.source.endswith("case2.robot")
        assert definition.lineno in (2, 8)


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_find_var_in_arg_passed(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${some var1}    1
${some var2}    2

*** Keywords ***
Put Key
    [Arguments]    ${key}    ${opts}=${some var1}
    ${ret}=    Create dictionary    ${key}=${some var2}
"""

    line, col = doc.get_last_line_col_with_contents(
        "Create dictionary    ${key}=${some var2}"
    )
    col -= len("e var2}")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 3


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_find_var_in_arg_received(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${some var1}    1
${some var2}    2

*** Keywords ***
Put Key
    [Arguments]    ${key}    ${opts}=${some var1}
    ${ret}=    Create dictionary    ${key}=${some var2}
"""

    line, col = doc.get_last_line_col_with_contents(
        "[Arguments]    ${key}    ${opts}=${some var1}"
    )
    col -= len("r1}")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 2


def test_find_definition_with_constructed_vars(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    [Setup]    Initialize Variables
    Log    ${SOME_VARIABLE_0}
    Log    ${SOME_VARIABLE_1}
    Log    ${SOME_VARIABLE_2}

*** Keywords ***
Initialize Variables
    FOR    ${index}    IN RANGE    3
        Set Test Variable    ${SOME_VARIABLE_${index}}    Value ${index}
    END
"""

    line, col = doc.get_last_line_col_with_contents("    Log    ${SOME_VARIABLE_0}")
    col -= len("E_0}")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 11


def test_vars_from_get_variables(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc_py = workspace.put_doc("vars.py")
    doc_py.source = """
def get_variables(arg):
    return {"PYTHON_VARIABLE": arg}
"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Variables    vars.py    arg1

*** Test Cases ***
Demo
    Log    ${PYTHON_VARIABLE}
"""

    line, col = doc.get_last_line_col_with_contents("    Log    ${PYTHON_VARIABLE}")
    col -= len("}")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("vars.py")
    assert definition.lineno == 2


def test_find_definition_suite_setup(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Suite Setup    Keyword1

*** Keyword ***
Keyword 1
"""

    line, col = doc.get_last_line_col_with_contents("Suite Setup    Keyword1")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 5


def test_find_definition_run_keyword_suite_setup(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Suite Setup    Run Keyword    Keyword1

*** Keyword ***
Keyword 1
"""

    line, col = doc.get_last_line_col_with_contents(
        "Suite Setup    Run Keyword    Keyword1"
    )
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 5


def test_find_definition_expression_var(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Demo
    ${var1}    Set Variable    2
    IF    ${{$var1 != "1"}}
        Fail
    END
"""

    line = doc.find_line_with_contents('    IF    ${{$var1 != "1"}}')
    col = len("    IF    ${{$v")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )

    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition.source.endswith("case2.robot")
    assert definition.lineno == 3
