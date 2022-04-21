from robocorp_ls_core.lsp import DocumentHighlightTypedDict
from typing import Optional, List
from robotframework_ls.impl.protocols import ICompletionContext, VarTokenInfo


def _highlight_keyword(
    completion_context: ICompletionContext, curr_token_info
) -> List[DocumentHighlightTypedDict]:
    from robotframework_ls.impl.references import (
        iter_keyword_references_in_doc,
        matches_source,
    )
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.protocols import IKeywordFound
    from robocorp_ls_core.lsp import DocumentHighlightKind

    ret: List[DocumentHighlightTypedDict] = []

    # We're in a keyword, so, search for matches.
    normalized_name = normalize_robot_name(curr_token_info.token.value)
    if curr_token_info.token.type == curr_token_info.token.KEYWORD:
        dot_i = normalized_name.find(".")
        if dot_i != -1:
            normalized_name = normalized_name[dot_i + 1 :]

    for range_ref in iter_keyword_references_in_doc(
        completion_context,
        completion_context.doc,
        normalized_name,
        keyword_found=None,  # We don't want to check it even if available (we want textual matches too even if not defined).
    ):
        completion_context.check_cancelled()
        ret.append({"range": range_ref, "kind": DocumentHighlightKind.Text})

    if curr_token_info.token.type == curr_token_info.token.KEYWORD_NAME:
        # We're hovering over the keyword name.
        ret.append(
            {
                "range": {
                    "start": {
                        "line": curr_token_info.token.lineno - 1,
                        "character": curr_token_info.token.col_offset,
                    },
                    "end": {
                        "line": curr_token_info.token.lineno - 1,
                        "character": curr_token_info.token.end_col_offset,
                    },
                },
                "kind": DocumentHighlightKind.Text,
            }
        )
    else:
        current_keyword_definition_and_usage_info = (
            completion_context.get_current_keyword_definition_and_usage_info()
        )
        if current_keyword_definition_and_usage_info is not None:
            # i.e.: check if the definition also matches.
            (
                keyword_definition,
                _usage_info,
            ) = current_keyword_definition_and_usage_info

            keyword_found: IKeywordFound = keyword_definition.keyword_found
            include_declaration = matches_source(
                completion_context.doc.path, keyword_found.source
            )
            if include_declaration:
                ret.append(
                    {
                        "range": {
                            "start": {
                                "line": keyword_found.lineno,
                                "character": keyword_found.col_offset,
                            },
                            "end": {
                                "line": keyword_found.end_lineno,
                                "character": keyword_found.end_col_offset,
                            },
                        },
                        "kind": DocumentHighlightKind.Text,
                    }
                )

    return ret


def _highlight_variables(
    completion_context: ICompletionContext, curr_token_info: VarTokenInfo
) -> List[DocumentHighlightTypedDict]:
    from robocorp_ls_core.lsp import DocumentHighlightKind
    from robotframework_ls.impl.references import iter_variable_references_in_doc
    from robotframework_ls.impl.find_definition import find_variable_definition

    ret: List[DocumentHighlightTypedDict] = []

    found_definitions = find_variable_definition(completion_context, curr_token_info)

    if not found_definitions:
        return ret

    if len(found_definitions) > 1:
        # Give preference for a global definition (in which case we'll provide
        # both globals as well as locals overriding the global).
        for definition in found_definitions:
            if not definition.variable_found.is_local_variable:
                break
        else:
            definition = next(iter(found_definitions))
    else:
        definition = next(iter(found_definitions))

    for range_ref in iter_variable_references_in_doc(
        completion_context,
        definition.variable_found,
    ):
        completion_context.check_cancelled()
        ret.append({"range": range_ref, "kind": DocumentHighlightKind.Text})

    return ret


def doc_highlight(
    completion_context: ICompletionContext,
) -> Optional[List[DocumentHighlightTypedDict]]:
    from robocorp_ls_core.lsp import DocumentHighlightKind

    curr_token_info = completion_context.get_current_token()
    if curr_token_info is None:
        return None

    ret: List[DocumentHighlightTypedDict] = []
    if curr_token_info.token.type in (
        curr_token_info.token.KEYWORD,
        curr_token_info.token.KEYWORD_NAME,
    ):
        return _highlight_keyword(completion_context, curr_token_info)

    curr_var_token_info = completion_context.get_current_variable()
    if curr_var_token_info is not None:
        return _highlight_variables(completion_context, curr_var_token_info)

    # We found no custom heuristics, just use a text-based approach.
    doc = completion_context.doc
    sel = completion_context.sel
    word_to_col = sel.word_at_column
    if not word_to_col:
        return ret

    contents = doc.source
    import re

    for m in re.finditer(f"\\b{re.escape(word_to_col)}\\b", contents):
        start = m.start(0)
        end = m.end(0)

        start_line, start_col = doc.offset_to_line_col(start)
        end_line, end_col = doc.offset_to_line_col(end)
        ret.append(
            {
                "range": {
                    "start": {
                        "line": start_line,
                        "character": start_col,
                    },
                    "end": {
                        "line": end_line,
                        "character": end_col,
                    },
                },
                "kind": DocumentHighlightKind.Text,
            }
        )
    return ret
