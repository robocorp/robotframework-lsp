from typing import List
from robocorp_ls_core.lsp import CompletionItemTypedDict
from robotframework_ls.impl.protocols import ICompletionContext

_SNIPPETS_RF4 = {
    "FOR IN": {
        "prefix": "FOR IN",
        "body": [
            "FOR<sp>${${1:element}}<sp>IN<sp>@{${2:LIST}}",
            "    Log<sp>${${1:element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN loop.\n\nA for loop that iterates over a list of values and assigns one value to a variable per iteration.",
    },
    "FOR IN ENUMERATE": {
        "prefix": "FOR IN ENUMERATE",
        "body": [
            "FOR<sp>${${1:index}}<sp>${${2:element}}<sp>IN ENUMERATE<sp>@{${3:LIST}}",
            "    Log<sp>${${1:index}}: ${${2:element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN ENUMERATE loop.\n\nA for loop that iterates over a list of values and assigns the iteration index to the first and the value to the second variable per iteration.",
    },
    "FOR IN RANGE": {
        "prefix": "FOR IN RANGE",
        "body": [
            "FOR<sp>${${1:counter}}<sp>IN RANGE<sp>${2:START}<sp>${3:END}<sp>${4:opt.STEPS}",
            "    Log<sp>${${1:counter}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN RANGE loop.\n\nA for loop that iterates over a range of values with an optional configurable step width.",
    },
    "FOR IN ZIP": {
        "prefix": "FOR IN ZIP",
        "body": [
            "FOR<sp>${${1:l1-element}}<sp>${${2:l2-element}}<sp>IN ZIP<sp>${${3:LIST-1}}<sp>${${4:LIST-2}}",
            "    Log<sp>${${1:l1-element}} - ${${2:l2-element}}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a FOR IN ZIP loop\n\nA for loop that iterates over two lists and assigns the values from the first list to the first variable and values from the second list to the second variable per iteration.",
    },
    "IF STATEMENT": {
        "prefix": "IF STATEMENT",
        "body": [
            "IF<sp>${1:\\$var_in_py_expr1 == \\$var_in_py_expr2}",
            "    $0",
            "END",
        ],
        "description": "Snippet of an IF..END statement.",
    },
    "IF ELSE STATEMENT": {
        "prefix": "IF ELSE STATEMENT",
        "body": [
            "IF<sp>${1:\\$var_in_py_expr1 == \\$var_in_py_expr2}",
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
            "Run Keyword If<sp>${1:\\$var_in_py_expr1 == \\$var_in_py_expr2}",
            "...    ${3:Keyword}<sp>${4:@args}",
            "...  ELSE IF<sp>${2:condition_in_py_expr}",
            "...    ${5:Keyword}<sp>${6:@args}",
            "...  ELSE",
            "...    ${7:Keyword}<sp>${8:@args}",
        ],
        "description": "Runs the given keyword with the given arguments, if condition is true.",
    },
    "Run Keywords": {
        "prefix": "Run Keywords",
        "body": [
            "Run Keywords",
            "...    ${1:Keyword}<sp>${2:@args}",
            "...  AND",
            "...    ${3:Keyword}<sp>${4:@args}",
        ],
        "description": "Executes all the given keywords in a sequence.",
    },
}

_SNIPPETS_RF5 = {
    "TRY EXCEPT STATEMENT": {
        "prefix": "TRY EXCEPT",
        "body": ["TRY", "    $0", "EXCEPT<sp>message", "    ", "END"],
        "description": "Snippet of a TRY..EXCEPT statement",
    },
    "TRY EXCEPT FINALLY STATEMENT": {
        "prefix": "TRY EXCEPT FINALLY",
        "body": [
            "TRY",
            "    $0",
            "EXCEPT<sp>message",
            "    ",
            "FINALLY",
            "    ",
            "END",
        ],
        "description": "Snippet of a TRY..EXCEPT..FINALLY statement",
    },
    "TRY FINALLY STATEMENT": {
        "prefix": "TRY FINALLY",
        "body": ["TRY", "    $0", "FINALLY", "    ", "END"],
        "description": "Snippet of a TRY..EXCEPT..FINALLY statement",
    },
    "WHILE STATEMENT": {
        "prefix": "WHILE",
        "body": [
            "WHILE<sp>${1:\\$var_in_py_expr1 == \\$var_in_py_expr2}",
            "    $0",
            "END",
        ],
        "description": "Snippet of a WHILE statement",
    },
    "WHILE STATEMENT UNLIMITED": {
        "prefix": "WHILE",
        "body": [
            "WHILE<sp>${1:\\$var_in_py_expr1 == \\$var_in_py_expr2}<sp>limit=NONE",
            "    $0",
            "END",
        ],
        "description": "Snippet of a WHILE statement with limit=NONE",
    },
    "CONTINUE": {
        "prefix": "CONTINUE",
        "body": ["CONTINUE"],
        "description": "Snippet for CONTINUE",
    },
    "BREAK": {
        "prefix": "BREAK",
        "body": ["BREAK"],
        "description": "Snippet for BREAK",
    },
    "RETURN": {
        "prefix": "RETURN",
        "body": ["RETURN"],
        "description": "Snippet for RETURN",
    },
    "ELSE": {
        "prefix": "ELSE",
        "body": ["ELSE"],
        "description": "Snippet for ELSE",
    },
}

_SNIPPETS_SORTED = None


def _get_global_snippets():
    from robotframework_ls.impl.robot_version import get_robot_major_version

    global _SNIPPETS_SORTED
    if _SNIPPETS_SORTED is None:
        use = {}
        use.update(_SNIPPETS_RF4)

        if get_robot_major_version() >= 5:
            use.update(_SNIPPETS_RF5)

        _SNIPPETS_SORTED = sorted(use.items())

    return _SNIPPETS_SORTED


def _create_completion_item_from_snippet(
    label, snippet, selection, line_to_col, separator_spaces
):
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
    from robocorp_ls_core.lsp import CompletionItemKind

    current_col = selection.col

    text = "\n".join(snippet["body"]).replace("<sp>", separator_spaces)

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
        documentation=snippet["description"] + "\n\n" + text,
        insertTextFormat=InsertTextFormat.Snippet,
    ).to_dict()


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    """
    Collects all the keywords that are available to the given completion_context.

    :param CompletionContext completion_context:
    """
    from robotframework_ls.robot_config import get_arguments_separator

    sel = completion_context.sel  #::type sel: DocumentSelection
    line_to_column = sel.line_to_column.lstrip().lower()
    if not line_to_column:
        return []

    separator_spaces = get_arguments_separator(completion_context)

    ret = []
    for label, data in _get_global_snippets():
        if line_to_column in data["prefix"].lower():
            ret.append(
                _create_completion_item_from_snippet(
                    label, data, sel, line_to_column, separator_spaces
                )
            )

    return ret
