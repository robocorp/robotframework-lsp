from typing import List

from robocorp_ls_core.lsp import CompletionItemTypedDict
from robocorp_ls_core.lsp import TextEditTypedDict
from robocorp_ls_core.lsp import InsertTextFormat
from robocorp_ls_core.lsp import CompletionItemKind
from robotframework_ls.impl.protocols import ICompletionContext
from robotframework_ls.impl.protocols import ILibraryImportNode
import os


def _iter_import_names(completion_context):
    imported_libraries = completion_context.get_imported_libraries()
    lib: ILibraryImportNode
    for lib in imported_libraries:
        alias = lib.alias
        if alias:
            use = alias
        else:
            use = lib.name
        if use.endswith(".py"):
            use = use[:-3]

        if use:
            yield use

    for resource_import in completion_context.get_resource_imports():
        use = resource_import.name
        use = os.path.splitext(use)[0]
        if use:
            yield use


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    ret: List[CompletionItemTypedDict] = []
    token_info = completion_context.get_current_token()
    if token_info is not None:
        keyword_usage = ast_utils.create_keyword_usage_info_from_token(
            token_info.stack, token_info.node, token_info.token
        )
        if keyword_usage is not None and "{" not in keyword_usage.token.value:
            full_tok_name = keyword_usage.token.value
            diff = token_info.token.end_col_offset - completion_context.sel.col
            if diff < 0:
                return ret
            if diff > 0:
                full_tok_name = full_tok_name[:-diff]

            replace_up_to_col = completion_context.sel.col

            curr_normalized = normalize_robot_name(full_tok_name).replace(".", "")

            for use in _iter_import_names(completion_context):
                i = use.rfind("}")
                if i >= 0:
                    use = use[i + 1 :]

                use = os.path.basename(use)

                if curr_normalized in normalize_robot_name(use).replace(".", ""):
                    text_edit: TextEditTypedDict = {
                        "range": {
                            "start": {
                                "line": completion_context.sel.line,
                                "character": token_info.token.col_offset,
                            },
                            "end": {
                                "line": completion_context.sel.line,
                                "character": replace_up_to_col,
                            },
                        },
                        "newText": use,
                    }

                    label = use
                    ret.append(
                        {
                            "label": label,
                            "kind": CompletionItemKind.Module,
                            "textEdit": text_edit,
                            "insertText": text_edit["newText"],
                            "insertTextFormat": InsertTextFormat.Snippet,
                        }
                    )

    return ret
