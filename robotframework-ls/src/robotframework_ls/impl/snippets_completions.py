_SNIPPETS = {
    "FOR IN": {
        "prefix": "FOR IN",
        "body": [
            "FOR    ${${1:element}}    IN    @{${2:LIST}}",
            "    Log    ${${1:element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN loop.\n\nA for loop that iterates over a list of values and assigns one value to a variable per iteration.",
    },
    "FOR IN ENUMERATE": {
        "prefix": "FOR IN ENUMERATE",
        "body": [
            "FOR    ${${1:index}}    ${${2:element}}    IN ENUMERATE    @{${3:LIST}}",
            "    Log    ${${1:index}}: ${${2:element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN ENUMERATE loop.\n\nA for loop that iterates over a list of values and assigns the iteration index to the first and the value to the second variable per iteration.",
    },
    "FOR IN RANGE": {
        "prefix": "FOR IN RANGE",
        "body": [
            "FOR    ${${1:counter}}    IN RANGE    ${2:START}    ${3:END}    ${4:opt.STEPS}",
            "    Log    ${${1:counter}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN RANGE loop.\n\nA for loop that iterates over a range of values with an optional configurable step width.",
    },
    "FOR IN ZIP": {
        "prefix": "FOR IN ZIP",
        "body": [
            "FOR    ${${1:l1-element}}    ${${2:l2-element}}    IN ZIP    ${${3:LIST-1}}    ${${4:LIST-2}}",
            "    Log    ${${1:l1-element}} - ${${2:l2-element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN ZIP loop\n\nA for loop that iterates over two lists and assigns the values from the first list to the first variable and values from the second list to the second variable per iteration.",
    },
    "IF STATEMENT": {
        "prefix": "IF STATEMENT",
        "body": ["IF    ${${1:var1}} == ${${1:var2}}", "    $0", "END"],
        "description": "Snippet of an IF..END statement.",
    },
    "IF ELSE STATEMENT": {
        "prefix": "IF ELSE STATEMENT",
        "body": [
            "IF    ${${1:var1}} == ${${1:var2}}",
            "    ${3:Call Keyword}",
            "ELSE",
            "    $0",
            "END",
        ],
        "description": "Snippet of an IF..ELSE..END statement",
    },
    "Run Keyword If": {
        "prefix": "Run Keyword If",
        "body": [
            "Run Keyword If    ${1:condition}",
            "...    ${3:Keyword}    ${4:@args}",
            "...  ELSE IF    ${2:condition}",
            "...    ${5:Keyword}    ${6:@args}",
            "...  ELSE",
            "...    ${7:Keyword}    ${8:@args}",
        ],
        "description": "Runs the given keyword with the given arguments, if condition is true.",
    },
    "Run Keywords": {
        "prefix": "Run Keywords",
        "body": [
            "Run Keywords",
            "...    ${1:Keyword}    ${2:@args}",
            "...  AND",
            "...    ${3:Keyword}    ${4:@args}",
        ],
        "description": "Executes all the given keywords in a sequence.",
    },
}

_SNIPPETS_SORTED = sorted(_SNIPPETS.items())


def _create_completion_item_from_snippet(label, snippet, selection, line_to_col):
    """
    :param selection: DocumentSelection
    """
    from robocorp_ls_core.lsp import (
        CompletionItem,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robocorp_ls_core.lsp import MarkupKind
    from robocorp_ls_core.lsp import CompletionItemKind

    current_col = selection.col

    text = "\n".join(snippet["body"])

    text_edit = TextEdit(
        Range(
            start=Position(selection.line, current_col - len(line_to_col)),
            end=Position(selection.line, current_col),
        ),
        text,
    )

    return CompletionItem(
        label,
        kind=CompletionItemKind.Snippet,
        text_edit=text_edit,
        insertText=text_edit.newText,
        documentation=snippet["description"] + "\n".join(["", ""] + snippet["body"]),
        insertTextFormat=InsertTextFormat.Snippet,
        documentationFormat=MarkupKind.Markdown,
    ).to_dict()


def complete(completion_context):
    """
    Collects all the keywords that are available to the given completion_context.
    
    :param CompletionContext completion_context:
    """
    sel = completion_context.sel  #::type sel: DocumentSelection
    line_to_column = sel.line_to_column.lstrip().lower()
    if not line_to_column:
        return []

    ret = []
    for label, data in _SNIPPETS_SORTED:
        if line_to_column in data["prefix"].lower():
            ret.append(
                _create_completion_item_from_snippet(label, data, sel, line_to_column)
            )

    return ret
