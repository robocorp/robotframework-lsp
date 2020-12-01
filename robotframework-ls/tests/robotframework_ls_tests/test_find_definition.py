from typing import Tuple


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


def test_find_definition_keyword_fixture(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc.source = doc.source + "\n    [Teardown]    my_Equal redefined"

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
    doc.source = doc.source + "\n*** Keywords ***\nTeardown    my_Equal redefined"

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
    doc = workspace.get_doc("case2.robot")
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
    doc = workspace.get_doc("case2.robot")
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
    doc = workspace.get_doc("case2.robot")
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
    doc = workspace.get_doc("case2.robot")
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
    doc = workspace.get_doc("case4.robot")
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
    doc.source = doc.source + "\n    BuiltIn.Should Be Empty"

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
    doc = workspace.get_doc("case4.robot")
    doc.source = """*** Settings ***
Library    Collections    WITH NAME    Col1

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
    doc = workspace.get_doc("case4.robot")
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
    doc = workspace.get_doc("case4.robot")
    doc.source = """*** Settings ***

Resource    case4resource.txt"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    definitions = find_definition(completion_context)
    assert len(definitions) == 1
    definition = next(iter(definitions))
    assert definition.source.endswith("case4resource.txt")


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
    doc.source += """
*** Test Cases ***
Returning
    ${variable_x} =    ${variable_y}    @{variable_z}=    Get X    an argument
    Log    We got ${variable_x}"""

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
    doc = workspace.get_doc("case4.robot")
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
    doc = workspace.get_doc("case4.robot")
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
    doc = workspace.get_doc("case4.robot")
    doc.source = """
*** Keywords ***
This is the Test
    [Arguments]    ${arg}    ${arg2}
    Log To Console    ${arg2}"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(
        _definitions_to_data_regression(find_definition(completion_context))
    )


def test_variables_completions_recursive(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.find_definition import find_definition

    workspace.set_root("case5", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case5.robot")
    doc.source += """

*** Test Cases ***
List Variable
    Log    ${VAR2}"""

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
    doc = workspace.get_doc("case4.robot")
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
