from typing import List, Dict, Any, Iterator
import typing

from robocorp_ls_core.lsp import (
    CommandTypedDict,
    ICustomDiagnosticDataTypedDict,
    ICustomDiagnosticDataUndefinedKeywordTypedDict,
    WorkspaceEditTypedDict,
    CompletionItemTypedDict,
    TextEditTypedDict,
    WorkspaceEditParamsTypedDict,
    ICustomDiagnosticDataUndefinedResourceTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import isinstance_name
import os
from pathlib import Path

log = get_logger(__name__)


def _add_import_code_action(
    completion_context: ICompletionContext,
    undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict,
) -> Iterator[CommandTypedDict]:
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robotframework_ls.impl import auto_import_completions

    keyword_name_to_keyword_found: Dict[
        str, List[IKeywordFound]
    ] = collect_keyword_name_to_keyword_found(completion_context)
    auto_imports_found: List[
        CompletionItemTypedDict
    ] = auto_import_completions.complete(
        completion_context, keyword_name_to_keyword_found, exact_match=True
    )

    for auto_import in auto_imports_found:
        label = auto_import["label"]
        if label.endswith("*"):
            label = label[:-1]

        lst: List[TextEditTypedDict] = []

        text_edit = auto_import["textEdit"]
        if text_edit:
            lst.append(text_edit)

        additional = auto_import["additionalTextEdits"]
        if additional:
            lst.extend(additional)

        changes = {completion_context.doc.uri: lst}
        edit: WorkspaceEditTypedDict = {"changes": changes}
        title = f"Import {label}"
        edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
        command: CommandTypedDict = {
            "title": title,
            "command": "robot.applyCodeAction",
            "arguments": [{"apply_edit": edit_params}],
        }

        yield command


def _create_keyword_in_current_file_text_edit(
    completion_context: ICompletionContext,
    undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict,
    keyword_template: str,
) -> TextEditTypedDict:
    from robotframework_ls.impl import ast_utils

    current_section: Any = completion_context.get_ast_current_section()
    if ast_utils.is_keyword_section(current_section):
        # Add it before the current keyword
        use_line = None
        for node in current_section.body:
            if isinstance_name(node, "Keyword"):
                node_lineno = node.lineno - 1

                if node_lineno <= completion_context.sel.line:
                    use_line = node_lineno
                else:
                    break

        if use_line is not None:
            return {
                "range": {
                    "start": {"line": use_line, "character": 0},
                    "end": {"line": use_line, "character": 0},
                },
                "newText": keyword_template,
            }

    keyword_section = ast_utils.find_keyword_section(completion_context.get_ast())
    if keyword_section is None:
        # We need to create the keyword section too
        current_section = completion_context.get_ast_current_section()
        if current_section is None:
            use_line = 1
        else:
            use_line = current_section.lineno - 1

        return {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": f"*** Keywords ***\n{keyword_template}",
        }

    else:
        # We add the keyword to the end of the existing keyword section
        use_line = keyword_section.end_lineno
        return {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": keyword_template,
        }


def _create_keyword_code_action(
    completion_context: ICompletionContext,
    undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict,
    keyword_template: str,
) -> Iterator[CommandTypedDict]:

    name = undefined_keyword_data["name"]
    if "." not in name:
        label = name
        lst: List[TextEditTypedDict] = [
            _create_keyword_in_current_file_text_edit(
                completion_context, undefined_keyword_data, keyword_template
            )
        ]

        changes = {completion_context.doc.uri: lst}
        edit: WorkspaceEditTypedDict = {"changes": changes}
        title = f"Create Keyword: {label} (in current file)"
        edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
        command: CommandTypedDict = {
            "title": title,
            "command": "robot.applyCodeAction",
            "arguments": [{"apply_edit": edit_params}],
        }

        yield command


def _undefined_resource_code_action(
    completion_context: ICompletionContext,
    undefined_resource_data: ICustomDiagnosticDataUndefinedResourceTypedDict,
) -> Iterator[CommandTypedDict]:
    from robocorp_ls_core.lsp import CreateFileTypedDict
    from robocorp_ls_core import uris

    name = undefined_resource_data["resolved_name"]
    if not name:
        name = undefined_resource_data["name"]
        if not name:
            return

    if "$" in name or "{" in name or "}" in name:
        return

    path = Path(os.path.join(os.path.dirname(completion_context.doc.path), name))
    create_doc_change: CreateFileTypedDict = {
        "kind": "create",
        "uri": uris.from_fs_path(str(path)),
    }
    edit: WorkspaceEditTypedDict = {"documentChanges": [create_doc_change]}
    title: str = f"Create {path.name} (at {path.parent})"
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}

    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_edit": edit_params}],
    }

    yield command


def _undefined_keyword_code_action(
    completion_context: ICompletionContext,
    undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict,
) -> Iterator[CommandTypedDict]:
    from robotframework_ls.robot_config import get_arguments_separator

    keyword_template = """$keyword_name$arguments\n\n"""
    # We'd like to have a cursor here, but alas, this isn't possible...
    # See: https://github.com/microsoft/language-server-protocol/issues/592
    # See: https://github.com/microsoft/language-server-protocol/issues/724
    keyword_name = undefined_keyword_data["name"]
    keyword_template = keyword_template.replace("$keyword_name", keyword_name)

    arguments: List[str] = []
    keyword_usage_info = completion_context.get_current_keyword_usage_info()
    if keyword_usage_info is not None:
        for token in keyword_usage_info.node.tokens:
            if token.type == token.ARGUMENT:
                if "=" in token.value:
                    name = token.value.split("=")[0]
                else:
                    name = token.value
                arguments.append(f"${{{name}}}")

    separator = get_arguments_separator(completion_context)
    args_str = ""
    if arguments:
        args_str += "\n    [Arguments]"
        for arg in arguments:
            args_str += separator
            args_str += arg
        args_str += "\n"

    keyword_template = keyword_template.replace("$arguments", args_str)

    yield from _add_import_code_action(completion_context, undefined_keyword_data)
    yield from _create_keyword_code_action(
        completion_context, undefined_keyword_data, keyword_template
    )


def code_action(
    completion_context: ICompletionContext,
    found_data: List[ICustomDiagnosticDataTypedDict],
) -> List[CommandTypedDict]:
    """
    Note: the completion context selection should be at the range end position.
    """

    ret: List[CommandTypedDict] = []
    for data in found_data:
        if data["kind"] == "undefined_keyword":
            undefined_keyword_data = typing.cast(
                ICustomDiagnosticDataUndefinedKeywordTypedDict, data
            )
            ret.extend(
                _undefined_keyword_code_action(
                    completion_context, undefined_keyword_data
                )
            )
        elif data["kind"] == "undefined_resource":
            undefined_keyword_data = typing.cast(
                ICustomDiagnosticDataUndefinedResourceTypedDict, data
            )
            ret.extend(
                _undefined_resource_code_action(
                    completion_context, undefined_keyword_data
                )
            )

    return ret
