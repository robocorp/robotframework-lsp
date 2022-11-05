from typing import List, Dict
import typing

from robocorp_ls_core.lsp import (
    CommandTypedDict,
    ICustomDiagnosticDataTypedDict,
    ICustomDiagnosticDataUndefinedKeywordTypedDict,
    WorkspaceEditTypedDict,
    CompletionItemTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound


def _add_import_code_action(completion_context) -> List[CommandTypedDict]:
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robotframework_ls.impl import auto_import_completions
    from robocorp_ls_core.lsp import WorkspaceEditParamsTypedDict
    from robocorp_ls_core.lsp import TextEditTypedDict

    keyword_name_to_keyword_found: Dict[
        str, List[IKeywordFound]
    ] = collect_keyword_name_to_keyword_found(completion_context)
    auto_imports_found: List[
        CompletionItemTypedDict
    ] = auto_import_completions.complete(
        completion_context, keyword_name_to_keyword_found, exact_match=True
    )

    ret: List[CommandTypedDict] = []
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
            "arguments": [edit_params],
        }

        ret.append(command)
    return ret


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
            ret.extend(_add_import_code_action(completion_context))
            # TODO: Add actions to create keyword
    return ret
