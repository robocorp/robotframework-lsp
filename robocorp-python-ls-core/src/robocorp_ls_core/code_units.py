"""
This module exists to make conversions of positions from/to the client.

By default the language server spec expects characters above the utf-16 range
to occupy 2 chars, so, something as:

a😃

logically (in python unicode) has 2 chars, but for the spec it needs to have
3 chars, so, we need to convert back and forth all positions to account for
this discrepancy.
"""

from robocorp_ls_core.protocols import (
    IDocument,
    IWorkspace,
    ITestInfoTypedDict,
    EvaluatableExpressionTypedDict,
)
from typing import List, Optional, Union, Iterable, Set
from robocorp_ls_core.lsp import (
    TextEditTypedDict,
    PositionTypedDict,
    DiagnosticsTypedDict,
    CompletionItemTypedDict,
    WorkspaceEditTypedDict,
    RangeTypedDict,
    LocationTypedDict,
    LocationLinkTypedDict,
    SelectionRangeTypedDict,
    CodeLensTypedDict,
    HoverTypedDict,
    DocumentHighlightTypedDict,
    CodeActionTypedDict,
    ShowDocumentParamsTypedDict,
)
import typing


def compute_utf16_code_units_len(s: str) -> int:
    if s.isascii():
        return len(s)

    tot = 0
    for c in s:
        tot += 1 if ord(c) < 65536 else 2
    return tot


def get_range_considering_utf16_code_units(s: str, start_col: int, end_col: int) -> str:
    if s.isascii():
        return s[start_col:end_col]

    if start_col == end_col:
        return ""

    assert end_col > start_col

    chars = []
    i = 0
    iter_in = iter(s)
    while start_col > i:
        c = next(iter_in)
        i += 1
        if ord(c) < 65536:
            continue
        i += 1

    while end_col > i:
        c = next(iter_in)
        chars.append(c)
        i += 1
        if ord(c) < 65536:
            continue
        i += 1

    return "".join(chars)


def convert_utf16_code_unit_to_python(s: str, col: int) -> int:
    if s.isascii():
        return col

    if col == 0:
        return 0

    tot = 0
    i = 0

    for c in s:
        tot += 1 if ord(c) < 65536 else 2
        i += 1
        if col == tot:
            return i

    return i


def convert_python_col_to_utf16_code_unit(
    d: IDocument,
    line,
    col,
    memo: Optional[dict] = None,
) -> int:
    if memo is not None:
        key = (line, col)
        try:
            return memo[key]
        except KeyError:
            pass

    line_contents = d.get_line(line)
    if line_contents.isascii():
        if memo is not None:
            memo[key] = col
        return col

    start_col = 0
    for i, c in enumerate(line_contents):
        if col == i:
            if memo is not None:
                memo[key] = start_col
            return start_col
        start_col += 1 if ord(c) < 65536 else 2

    if memo is not None:
        memo[key] = start_col
    return start_col


def _convert_start_end_range_python_code_unit_to_utf16_inplace(
    d: IDocument,
    start_pos: PositionTypedDict,
    end_pos: PositionTypedDict,
    memo: Optional[dict] = None,
) -> None:
    start_pos["character"] = convert_python_col_to_utf16_code_unit(
        d, start_pos["line"], start_pos["character"], memo=memo
    )
    end_pos["character"] = convert_python_col_to_utf16_code_unit(
        d, end_pos["line"], end_pos["character"], memo=memo
    )


def convert_range_pos_to_client_inplace(
    d: IDocument,
    r: RangeTypedDict,
    memo: Optional[dict] = None,
) -> RangeTypedDict:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    start_pos = r["start"]
    end_pos = r["end"]
    start_pos["character"] = convert_python_col_to_utf16_code_unit(
        d, start_pos["line"], start_pos["character"], memo=memo
    )
    end_pos["character"] = convert_python_col_to_utf16_code_unit(
        d, end_pos["line"], end_pos["character"], memo=memo
    )
    return r


def convert_location_or_location_link_pos_to_client_inplace(
    d: IDocument,
    location: Union[LocationTypedDict, LocationLinkTypedDict],
) -> Union[LocationTypedDict, LocationLinkTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    memo: dict = {}

    if "range" in location:
        loc = typing.cast(LocationTypedDict, location)
        r = loc["range"]
        convert_range_pos_to_client_inplace(d, r, memo)
    else:
        loc_link = typing.cast(LocationLinkTypedDict, location)

        r = loc_link["originSelectionRange"]
        convert_range_pos_to_client_inplace(d, r, memo)

        r = loc_link["targetRange"]
        convert_range_pos_to_client_inplace(d, r, memo)

        r = loc_link["targetSelectionRange"]
        convert_range_pos_to_client_inplace(d, r, memo)

    return location


def _iter_ranges_from_selection_range(
    selection_range: SelectionRangeTypedDict, visited: Set[int]
) -> Iterable[RangeTypedDict]:
    key = id(selection_range)
    if key not in visited:
        visited.add(key)
        yield selection_range["range"]

    parent = selection_range.get("parent")
    if parent:
        yield from _iter_ranges_from_selection_range(parent, visited)


def convert_selection_range_pos_to_client_inplace(
    d: IDocument,
    selection_ranges: List[SelectionRangeTypedDict],
    memo: Optional[dict] = None,
) -> List[SelectionRangeTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    visited: Set[int] = set()

    for selection_range in selection_ranges:
        for text_range in _iter_ranges_from_selection_range(selection_range, visited):
            _convert_start_end_range_python_code_unit_to_utf16_inplace(
                d, text_range["start"], text_range["end"], memo=memo
            )
    return selection_ranges


def convert_text_edits_pos_to_client_inplace(
    d: IDocument, text_edits: List[TextEditTypedDict], memo: Optional[dict] = None
) -> List[TextEditTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    for text_edit in text_edits:
        text_range = text_edit["range"]
        _convert_start_end_range_python_code_unit_to_utf16_inplace(
            d, text_range["start"], text_range["end"], memo=memo
        )
    return text_edits


def convert_code_lens_pos_to_client_inplace(
    d: IDocument, code_lens: List[CodeLensTypedDict], memo: Optional[dict] = None
) -> List[CodeLensTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    for code_len in code_lens:
        text_range = code_len["range"]
        _convert_start_end_range_python_code_unit_to_utf16_inplace(
            d, text_range["start"], text_range["end"], memo=memo
        )
    return code_lens


def convert_tests_pos_to_client_inplace(
    d: IDocument, tests: List[ITestInfoTypedDict], memo: Optional[dict] = None
) -> List[ITestInfoTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    for test in tests:
        text_range = test["range"]
        _convert_start_end_range_python_code_unit_to_utf16_inplace(
            d, text_range["start"], text_range["end"], memo=memo
        )
    return tests


def convert_evaluatable_expression_pos_to_client_inplace(
    d: IDocument,
    evaluatable_expr: Optional[EvaluatableExpressionTypedDict],
    memo: Optional[dict] = None,
) -> Optional[EvaluatableExpressionTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    if evaluatable_expr:
        text_range = evaluatable_expr["range"]
        _convert_start_end_range_python_code_unit_to_utf16_inplace(
            d, text_range["start"], text_range["end"], memo=memo
        )
    return evaluatable_expr


def convert_hover_pos_to_client_inplace(
    d: IDocument,
    hover: Optional[HoverTypedDict],
    memo: Optional[dict] = None,
) -> Optional[HoverTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    if hover:
        text_range = hover.get("range")
        if text_range:
            _convert_start_end_range_python_code_unit_to_utf16_inplace(
                d, text_range["start"], text_range["end"], memo=memo
            )
    return hover


def convert_document_highlight_pos_to_client_inplace(
    d: IDocument,
    doc_highlight_list: Optional[List[DocumentHighlightTypedDict]],
    memo: Optional[dict] = None,
) -> Optional[List[DocumentHighlightTypedDict]]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    if memo is None:
        memo = {}

    if doc_highlight_list:
        for doc_highlight in doc_highlight_list:
            text_range = doc_highlight.get("range")
            if text_range:
                _convert_start_end_range_python_code_unit_to_utf16_inplace(
                    d, text_range["start"], text_range["end"], memo=memo
                )
    return doc_highlight_list


def convert_diagnostics_pos_to_client_inplace(
    d: IDocument, diagnostics: List[DiagnosticsTypedDict]
) -> List[DiagnosticsTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    memo: dict = {}
    for diagnostic in diagnostics:
        text_range = diagnostic["range"]
        _convert_start_end_range_python_code_unit_to_utf16_inplace(
            d, text_range["start"], text_range["end"], memo=memo
        )
    return diagnostics


def convert_completions_pos_to_client_inplace(
    d: IDocument, completion_items: List[CompletionItemTypedDict]
) -> List[CompletionItemTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    memo: dict = {}
    for completion_item in completion_items:
        text_edit = completion_item.get("textEdit")
        if text_edit:
            text_range = text_edit["range"]
            _convert_start_end_range_python_code_unit_to_utf16_inplace(
                d, text_range["start"], text_range["end"], memo=memo
            )
        additional_text_edits = completion_item.get("additionalTextEdits")
        if additional_text_edits:
            convert_text_edits_pos_to_client_inplace(
                d, additional_text_edits, memo=memo
            )
    return completion_items


def convert_workspace_edit_pos_to_client_inplace(
    workspace: IWorkspace, workspace_edit: WorkspaceEditTypedDict
) -> WorkspaceEditTypedDict:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    changes = workspace_edit.get("changes")
    if changes:
        for doc_uri, text_edits in changes.items():
            doc = workspace.get_document(doc_uri, accept_from_file=True)
            if doc:
                convert_text_edits_pos_to_client_inplace(doc, text_edits)

    return workspace_edit


def convert_references_pos_to_client_inplace(
    workspace: IWorkspace, curr_doc: IDocument, references: List[LocationTypedDict]
) -> List[LocationTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    for reference in references:
        uri = reference["uri"]
        if uri == curr_doc.uri:
            convert_location_or_location_link_pos_to_client_inplace(curr_doc, reference)
        else:
            doc = workspace.get_document(uri, accept_from_file=True)
            if doc is not None:
                convert_location_or_location_link_pos_to_client_inplace(doc, reference)

    return references


def convert_code_action_pos_to_client_inplace(
    workspace: IWorkspace, code_action_list: List[CodeActionTypedDict]
) -> List[CodeActionTypedDict]:
    """
    Note: changes contents in-place. Returns the same input to help on composability.
    """
    for code_action in code_action_list:
        command = code_action.get("command")
        if not command:
            continue
        arguments = command.get("arguments")
        if not arguments:
            continue

        if not isinstance(arguments, list):
            continue

        for argument in arguments:
            if isinstance(argument, dict):
                apply_snippet = argument.get("apply_snippet")
                if apply_snippet:
                    workspace_edit = apply_snippet.get("edit")
                    if workspace_edit:
                        convert_workspace_edit_pos_to_client_inplace(
                            workspace, workspace_edit
                        )
                apply_edit = argument.get("apply_edit")
                if apply_edit:
                    workspace_edit = apply_edit.get("edit")
                    if workspace_edit:
                        convert_workspace_edit_pos_to_client_inplace(
                            workspace, workspace_edit
                        )

                # The show document depends on the contents written to the disk as
                # it'll usually reference the language server edit, so, it has to
                # be built with the proper calculated offsets.
                # show_document: Optional[ShowDocumentParamsTypedDict] = argument.get(
                #     "show_document"
                # )
                # if show_document:
                #     uri = show_document.get("uri")
                #     selection = show_document.get("selection")
                #     if selection and uri:
                #         doc = workspace.get_document(uri, accept_from_file=True)
                #         if doc:
                #             convert_range_pos_to_client_inplace(doc, selection)

    return code_action_list
