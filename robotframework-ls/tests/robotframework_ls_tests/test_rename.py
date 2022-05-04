import pytest

from robocorp_ls_core.constants import NULL
from robocorp_ls_core.jsonrpc.exceptions import JsonRpcException
from robocorp_ls_core.lsp import LSPMessages, MessageType


def check_data_regression(result, data_regression, basename=None):
    from robocorp_ls_core import uris
    import os.path

    data = {}
    for uri, text_edits in result.items():
        as_fs_path = uris.to_fs_path(uri)

        name = os.path.basename(as_fs_path.replace("\\", "/"))
        if name.endswith(".py"):
            raise AssertionError("Did not expect .py to be renamed.")

        data[name] = text_edits

    data_regression.check(sorted(data.items()), basename=basename)


def test_prepare_rename_wrong(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import prepare_rename

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.get_doc("case4resource3.robot")

    line = doc.find_line_with_contents("[Arguments]         ${arg1}     ${arg2}")
    col = 0
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    with pytest.raises(JsonRpcException) as e:
        prepare_rename(completion_context)
    assert (
        "Unable to rename (could not find keyword nor variable in current position)."
        in str(e)
    )


def test_rename_from_keyword_definition(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import rename, prepare_rename

    workspace.set_root("case4", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.get_doc("case4resource3.robot")

    line = doc.find_line_with_contents("Yet Another Equal Redefined")
    col = 6
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = prepare_rename(completion_context)
    data_regression.check(
        result,
        basename="test_rename_from_keyword_definition.prepare",
    )
    result = rename(completion_context, "Rara")
    assert result

    check_data_regression(result["changes"], data_regression)


def test_rename_keyword_name_dotted(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import rename, prepare_rename

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Library    Collections

*** Test Cases ***
Check
    ${list}=    Evaluate    []
    Collections.appendtolist    ${list}    a    b
    Append to list    ${list}    a    b
"""

    line = doc.find_line_with_contents("    Append to list    ${list}    a    b")
    col = len("    Append to li")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = prepare_rename(completion_context)
    data_regression.check(
        result,
        basename="test_rename_keyword_name_dotted.prepare",
    )
    result = rename(completion_context, "Rara")
    assert result

    check_data_regression(result["changes"], data_regression)


def test_rename_from_variable_definition(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import rename

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Keywords ***
Example1
    ${foo}=    Set Variable    ${None}
    Log To Console    ${foo}
    
Example2 
    ${foo}=    Set Variable    ${None}
    Log To Console    ${foo}
    """,
    )
    line = doc.find_line_with_contents("    ${foo}=    Set Variable    ${None}")
    col = 7
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    result = rename(completion_context, new_name="bar")
    assert result
    check_data_regression(result["changes"], data_regression)


class _DummyLspMessages(LSPMessages):
    def __init__(self):
        LSPMessages.__init__(self, NULL)
        self.messages = []

    def show_message(self, message, msg_type=MessageType.Info):
        self.messages.append(message)


def test_rename_builtin_references(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import rename, prepare_rename

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** keywords ***
Example2 
    ${foo}=    Set Variable    ${None}
    Log To Console    ${foo}
    """,
    )
    line = doc.find_line_with_contents("    Log To Console    ${foo}")
    col = 9
    completion_context = CompletionContext(
        doc,
        workspace=workspace.ws,
        line=line,
        col=col,
        lsp_messages=_DummyLspMessages(),
    )
    result = prepare_rename(completion_context)
    assert result

    assert completion_context.lsp_messages.messages == [
        "Keyword defined in Library. Only references will be renamed "
        "(the 'Log To Console' definition in 'BuiltIn' will need to be renamed manually)."
    ]
    result = rename(completion_context, new_name="bar")
    check_data_regression(result["changes"], data_regression)


def test_rename_keyword_name_with_variables(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import prepare_rename

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc(
        "case2.robot",
        """
*** Test Cases ***
Check
    Key 22 with args

*** Keywords ***
Key ${a} with args
    Log to console    ${a}
    """,
    )
    line = doc.find_line_with_contents("    Key 22 with args")
    col = 6
    completion_context = CompletionContext(
        doc,
        workspace=workspace.ws,
        line=line,
        col=col,
        lsp_messages=_DummyLspMessages(),
    )
    with pytest.raises(JsonRpcException) as e:
        prepare_rename(completion_context)

    assert (
        "Unable to rename 'Key ${a} with args' "
        "(keywords with variables embedded in the name cannot be renamed)." in str(e)
    )


def test_rename_var_with_constructed_vars(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.rename import prepare_rename

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

    with pytest.raises(JsonRpcException) as e:
        prepare_rename(completion_context)
