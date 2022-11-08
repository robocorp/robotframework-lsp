from robocorp_ls_core.lsp import CompletionItemTypedDict, CompletionItemKind
from typing import Any, List, Optional
from robocorp_ls_core.protocols import TypedDict


class MonacoCompletionItemKind:
    Method = 0
    Function = 1
    Constructor = 2
    Field = 3
    Variable = 4
    Class = 5
    Struct = 6
    Interface = 7
    Module = 8
    Property = 9
    Event = 10
    Operator = 11
    Unit = 12
    Value = 13
    Constant = 14
    Enum = 15
    EnumMember = 16
    Keyword = 17
    Text = 18
    Color = 19
    File = 20
    Reference = 21
    Customcolor = 22
    Folder = 23
    TypeParameter = 24
    User = 25
    Issue = 26
    Snippet = 27


_lsp_completion_item_kind_to_monaco = {
    CompletionItemKind.Method: MonacoCompletionItemKind.Method,
    CompletionItemKind.Function: MonacoCompletionItemKind.Function,
    CompletionItemKind.Constructor: MonacoCompletionItemKind.Constructor,
    CompletionItemKind.Field: MonacoCompletionItemKind.Field,
    CompletionItemKind.Variable: MonacoCompletionItemKind.Variable,
    CompletionItemKind.Class: MonacoCompletionItemKind.Class,
    CompletionItemKind.Interface: MonacoCompletionItemKind.Interface,
    CompletionItemKind.Struct: MonacoCompletionItemKind.Struct,
    CompletionItemKind.Module: MonacoCompletionItemKind.Module,
    CompletionItemKind.Property: MonacoCompletionItemKind.Property,
    CompletionItemKind.Unit: MonacoCompletionItemKind.Unit,
    CompletionItemKind.Value: MonacoCompletionItemKind.Value,
    CompletionItemKind.Constant: MonacoCompletionItemKind.Constant,
    CompletionItemKind.Enum: MonacoCompletionItemKind.Enum,
    CompletionItemKind.EnumMember: MonacoCompletionItemKind.EnumMember,
    CompletionItemKind.Keyword: MonacoCompletionItemKind.Keyword,
    CompletionItemKind.Snippet: MonacoCompletionItemKind.Snippet,
    CompletionItemKind.Text: MonacoCompletionItemKind.Text,
    CompletionItemKind.Color: MonacoCompletionItemKind.Color,
    CompletionItemKind.File: MonacoCompletionItemKind.File,
    CompletionItemKind.Reference: MonacoCompletionItemKind.Reference,
    CompletionItemKind.Folder: MonacoCompletionItemKind.Folder,
    CompletionItemKind.Event: MonacoCompletionItemKind.Event,
    CompletionItemKind.Operator: MonacoCompletionItemKind.Operator,
    CompletionItemKind.TypeParameter: MonacoCompletionItemKind.TypeParameter,
    CompletionItemKind.User: MonacoCompletionItemKind.User,
    CompletionItemKind.Issue: MonacoCompletionItemKind.Issue,
}


class MonacoCommandTypedDict(TypedDict, total=False):
    id: str
    title: str
    tooltip: Optional[str]
    arguments: Optional[list]


class MonacoCompletionItemTypedDict(TypedDict, total=False):
    #
    # The label of this completion item. By default
    # this is also the text that is inserted when selecting
    # this completion.
    #
    label: str  # string | CompletionItemLabel
    #
    # The kind of this completion item. Based on the kind
    # an icon is chosen by the editor.
    #
    kind: int  # MonacoCompletionItemKind
    #
    # A modifier to the `kind` which affect how the item
    # is rendered, e.g. Deprecated is rendered with a strikeout
    #
    tags: Optional[List[Any]]  # ReadonlyArray<CompletionItemTag>
    #
    # A human-readable string with additional information
    # about this item, like type or symbol information.
    #
    detail: Optional[str]
    #
    # A human-readable string that represents a doc-comment.
    #
    documentation: Optional[str]  # string | IMarkdownString
    #
    # A string that should be used when comparing this item
    # with other items. When `falsy` the [label](#CompletionItem.label)
    # is used.
    #
    sortText: Optional[str]
    #
    # A string that should be used when filtering a set of
    # completion items. When `falsy` the [label](#CompletionItem.label)
    # is used.
    #
    filterText: Optional[str]
    #
    # Select this item when showing. *Note* that only one completion item can be selected and
    # that the editor decides which item that is. The rule is that the *first* item of those
    # that match best is selected.
    #
    preselect: Optional[bool]
    #
    # A string or snippet that should be inserted in a document when selecting
    # this completion.
    # is used.
    #
    insertText: str
    #
    # Addition rules (as bitmask) that should be applied when inserting
    # this completion.
    #
    insertTextRules: Optional[Any]  # CompletionItemInsertTextRule
    #
    # A range of text that should be replaced by this completion item.
    #
    # Defaults to a range from the start of the [current word](#TextDocument.getWordRangeAtPosition) to the
    # current position.
    #
    # *Note:* The range must be a [single line](#Range.isSingleLine) and it must
    # [contain](#Range.contains) the position at which completion has been [requested](#CompletionItemProvider.provideCompletionItems).
    #
    range: Optional[Any]  # IRange | {insert: IRange; replace: IRange}
    #
    # An optional set of characters that when pressed while this completion is active will accept it first and
    # then type that character. *Note* that all commit characters should have `length=1` and that superfluous
    # characters will be ignored.
    #
    commitCharacters: Optional[List[str]]
    #
    # An optional array of additional text edits that are applied when
    # selecting this completion. Edits must not overlap with the main edit
    # nor with themselves.
    #
    additionalTextEdits: Optional[Any]  # editor.ISingleEditOperation[]
    #
    # A command that should be run upon acceptance of this item.
    #
    command: Optional[MonacoCommandTypedDict]

    # Not really in the official docs, but if present it'll be persisted
    # so that it's possible to resolve a completion item.
    data: Any


class CompletionItemInsertTextRule:
    #
    # Adjust whitespace/indentation of multiline insert texts to
    # match the current line indentation.
    # /
    KeepWhitespace = 1
    #
    # `insertText` is a snippet.
    InsertAsSnippet = 4


def convert_to_monaco_completion(
    lsp_completion: CompletionItemTypedDict, line_delta: int, col_delta: int, uri: str
) -> MonacoCompletionItemTypedDict:
    """
    Completions from monaco are different from the completions in the language
    server, so, we need to convert from one to the other.
    """
    from robocorp_ls_core.lsp import InsertTextFormat

    documentation = lsp_completion.get("documentation")
    if isinstance(documentation, dict):  # MarkupContent
        # Should render if markdown...
        documentation = documentation.get("value", "")

    insert_text_format = lsp_completion.get(
        "insertTextFormat", InsertTextFormat.PlainText
    )
    insert_text_rules = 0
    if insert_text_format == InsertTextFormat.Snippet:
        insert_text_rules |= CompletionItemInsertTextRule.InsertAsSnippet

    if lsp_completion.get("insertTextMode") == 2:
        insert_text_rules |= CompletionItemInsertTextRule.KeepWhitespace

    label: str = lsp_completion["label"]
    insert_text: str = lsp_completion.get("insertText", label)  # type: ignore

    text_edit = lsp_completion.get("textEdit")
    range_: Any = None
    if text_edit:
        insert_text = text_edit["newText"]
        range_ = text_edit["range"]
        if range_:
            # Note: must convert from 0-based to 1-based
            range_["startLineNumber"] = range_["start"]["line"] - line_delta + 1
            range_["startColumn"] = range_["start"]["character"] - col_delta + 1
            range_["endLineNumber"] = range_["end"]["line"] - line_delta + 1
            range_["endColumn"] = range_["end"]["character"] - col_delta + 1

    # Note: we don't cover all, just the things we know are required for the robot lsp usage.
    ret: MonacoCompletionItemTypedDict = {
        "label": label,
        "kind": _lsp_completion_item_kind_to_monaco.get(lsp_completion["kind"], 0),
        "insertText": insert_text,
        "insertTextRules": insert_text_rules,
    }
    if documentation is not None:
        ret["documentation"] = documentation

    if range_ is not None:
        ret["range"] = range_

    sort_text = lsp_completion.get("sortText")
    if sort_text is not None:
        ret["sortText"] = sort_text

    filter_text = lsp_completion.get("filterText")
    if filter_text is not None:
        ret["filterText"] = filter_text

    preselect = lsp_completion.get("preselect")
    if preselect is not None:
        ret["preselect"] = preselect

    detail = lsp_completion.get("detail")
    if detail is not None:
        ret["detail"] = detail

    data = lsp_completion.get("data")
    if data is not None:
        ret["data"] = data

    additional_text_edits = lsp_completion.get("additionalTextEdits")
    if additional_text_edits is not None:
        # Ok, it seems we have some auto-import. Changing the console contents
        # is actually pretty tricky if the user was editing a task as it'd need
        # to actually create a *** Settings *** and a *** Tasks *** and reindent.
        # all the contents (it may not actually be all that difficult, but then
        # the final result to the user may be a bit surprising).
        # So, instead of doing that, a command is issued to add the
        # related import directly to the console.
        if additional_text_edits and len(additional_text_edits) == 1:
            text_edit = additional_text_edits[0]
            command: MonacoCommandTypedDict = {
                "title": "Interactive Console",
                "id": "robot.completion.additionalTextEdit",
                "arguments": [{"code": text_edit["newText"], "uri": uri}],
            }
            ret["command"] = command
    return ret
