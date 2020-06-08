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
