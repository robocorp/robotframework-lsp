from typing import List

from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.protocols import IDocumentSelection


def _create_completion_item(
    label: str,
    new_text: str,
    selection: IDocumentSelection,
    col_start: int,
    col_end: int,
    documentation: str,
) -> dict:
    from robocorp_ls_core.lsp import (
        CompletionItem,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robocorp_ls_core.lsp import CompletionItemKind

    text_edit = TextEdit(
        Range(
            start=Position(selection.line, col_start),
            end=Position(selection.line, col_end),
        ),
        new_text,
    )

    return CompletionItem(
        label,
        kind=CompletionItemKind.Field,
        text_edit=text_edit,
        insertText=label,
        documentation=documentation,
        insertTextFormat=InsertTextFormat.PlainText,
    ).to_dict()


def complete(completion_context: ICompletionContext) -> List[dict]:
    from robotframework_ls.impl.protocols import IKeywordFound
    from robotframework_ls.impl.protocols import IKeywordArg

    ret: List[dict] = []
    sel = completion_context.sel
    if sel.word_from_column:
        # i.e.: if there's any word after the column, skip it (could work, but
        # let's simplify for now).
        return ret

    token_info = completion_context.get_current_token()
    if token_info and token_info.token:
        token = token_info.token

        if token.type not in (token.ARGUMENT, token.EOL):
            return []

    current_keyword_definition = completion_context.get_current_keyword_definition()
    if current_keyword_definition is not None:
        keyword_found: IKeywordFound = current_keyword_definition.keyword_found
        keyword_args = keyword_found.keyword_args
        if keyword_args:
            curr_token_value = token.value

            if "=" in curr_token_value:
                return ret

            # Note: If it's an empty word, it's okay to be in the middle.
            if token.end_col_offset > sel.col and curr_token_value.strip():
                return []

            word_to_column = curr_token_value.strip()

            arg: IKeywordArg
            for arg in keyword_args:
                if arg.is_keyword_arg or arg.is_star_arg:
                    continue

                arg_name = arg.arg_name

                if arg_name.startswith("${") and arg_name.endswith("}"):
                    arg_name = arg_name[2:-1]

                arg_name = arg_name.strip()
                if arg_name:
                    arg_name += "="

                col_start = sel.col
                col_end = sel.col
                new_text = arg_name
                if word_to_column:
                    if not arg_name.startswith(word_to_column):
                        continue
                    new_text = arg_name[len(word_to_column) :]

                documentation = arg.original_arg

                ret.append(
                    _create_completion_item(
                        arg_name, new_text, sel, col_start, col_end, documentation
                    )
                )

    return ret
