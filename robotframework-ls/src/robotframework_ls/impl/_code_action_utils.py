from typing import List, Optional

from robocorp_ls_core.lsp import (
    TextEditTypedDict,
    CodeActionTypedDict,
    WorkspaceEditTypedDict,
    WorkspaceEditParamsTypedDict,
    CommandTypedDict,
    RangeTypedDict,
    ShowDocumentParamsTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext


def wrap_edits_in_snippet(
    completion_context: ICompletionContext,
    title,
    text_edits: List[TextEditTypedDict],
    kind: str,
) -> CodeActionTypedDict:
    changes = {completion_context.doc.uri: text_edits}
    edit: WorkspaceEditTypedDict = {"changes": changes}
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_snippet": edit_params}],
    }
    return {"title": title, "kind": kind, "command": command}


def wrap_edit_in_command(
    completion_context: ICompletionContext, title, text_edit: TextEditTypedDict
) -> CodeActionTypedDict:
    changes = {completion_context.doc.uri: [text_edit]}
    edit: WorkspaceEditTypedDict = {"changes": changes}
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_edit": edit_params}],
    }
    add_show_document_at_command(command, completion_context.doc.uri, text_edit)

    return {"title": title, "kind": "quickfix", "command": command}


def add_show_document_at_command(
    command: CommandTypedDict,
    doc_uri: str,
    text_edit: Optional[TextEditTypedDict] = None,
):
    if text_edit:
        new_text = text_edit["newText"]
        cursor_i = new_text.find("$__LSP_CURSOR_LOCATION__$")
        if cursor_i == -1:
            endline = text_edit["range"]["end"]["line"]
            endchar = text_edit["range"]["end"]["character"]
        else:
            endline = text_edit["range"]["start"]["line"]
            endchar = text_edit["range"]["start"]["character"]
            # Find the actual cursor_i location (and remove it from the text)
            text_edit["newText"] = new_text.replace("$__LSP_CURSOR_LOCATION__$", "", 1)
            for line_i, text in enumerate(new_text.splitlines()):
                if "$__LSP_CURSOR_LOCATION__$" in text:
                    endline += line_i
                    endchar += text.find("$__LSP_CURSOR_LOCATION__$")
                    break

    else:
        endline = 0
        endchar = 0

    selection: RangeTypedDict = {
        "start": {"line": endline, "character": endchar},
        "end": {"line": endline, "character": endchar},
    }
    show_document: ShowDocumentParamsTypedDict = {
        "uri": doc_uri,
        "selection": selection,
        "takeFocus": True,
    }

    arguments = command["arguments"]
    if arguments:
        arguments[0]["show_document"] = show_document
