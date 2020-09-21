from typing import List

from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.protocols import IDocumentSelection


def _create_completion_item(
    label, new_text, selection: IDocumentSelection, col_start, col_end
) -> dict:
    from robocorp_ls_core.lsp import (
        CompletionItem,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robocorp_ls_core.lsp import MarkupKind
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
        documentation="",
        insertTextFormat=InsertTextFormat.PlainText,
        documentationFormat=MarkupKind.PlainText,
    ).to_dict()


def complete(completion_context: ICompletionContext) -> List[dict]:
    from robotframework_ls.impl.protocols import IKeywordFound

    ret: List[dict] = []
    sel = completion_context.sel
    if sel.word_from_column:
        # i.e.: if there's any word after the column, skip it (could work, but
        # let's simplify for now).
        return ret

    current_keyword_definition = completion_context.get_current_keyword_definition()
    if current_keyword_definition is not None:
        keyword_found: IKeywordFound = current_keyword_definition.keyword_found
        keyword_args = keyword_found.keyword_args
        if keyword_args:
            word_to_column = sel.word_to_column
            contents_without_word = sel.line_to_column
            if word_to_column:
                contents_without_word = contents_without_word[: -len(word_to_column)]

            for c in reversed(contents_without_word):
                # If we have something as `Some keyword    param=xxx|`
                # we don't want completions.
                if c in (" ", "\t"):
                    continue
                if c == "=":
                    return ret

            for arg in keyword_args:
                if arg.startswith("${") and arg.endswith("}"):
                    arg = arg[2:-1]

                if arg.startswith("**"):
                    continue

                elif arg.startswith("*"):
                    continue

                eq_i = arg.rfind("=")
                if eq_i != -1:
                    arg = arg[:eq_i]

                colon_i = arg.rfind(":")
                if colon_i != -1:
                    arg = arg[:colon_i]

                arg = arg.strip()
                if arg:
                    arg += "="

                col_start = sel.col
                col_end = sel.col
                new_text = arg
                if word_to_column:
                    if not arg.startswith(word_to_column):
                        continue
                    new_text = arg[len(word_to_column) :]

                ret.append(
                    _create_completion_item(arg, new_text, sel, col_start, col_end)
                )

    return ret
