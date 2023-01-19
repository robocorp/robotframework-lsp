from robocorp_ls_core.protocols import IDocument, IWorkspace
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

    for attr in (
        "range",
        "originSelectionRange",
        "targetRange",
        "targetSelectionRange",
    ):
        r = typing.cast(Optional[RangeTypedDict], location.get(attr))
        if r is not None:
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
