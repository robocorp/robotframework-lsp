from robotframework_ls.impl.completion_context import CompletionContext
from typing import List, Tuple
from robocorp_ls_core.protocols import IDocument


TOKEN_TYPES = [
    "parameter",
    "variable",
    "comment",
    # Custom added
    "header",  # entity.name.type.class.robot  -- *** Settings ***
    "setting",  # storage.type.setting.robot  -- Resource, Library
    "name",  # entity.other.inherited-class.robot   -- my.library.py
    "keywordNameDefinition",  # entity.name.function.robot
    "variableOperator",  # keyword.operator.variable.robot
    "keywordNameCall",  # meta.keyword.call.robot
    "settingOperator",  # keyword.operator.setting.robot
    "control",
    "testCaseName",
]

TOKEN_MODIFIERS = [
    "declaration",
    "definition",
    "readonly",
    "static",
    "deprecated",
    "abstract",
    "async",
    "modification",
    "documentation",
    "defaultLibrary",
]

TOKEN_TYPE_TO_INDEX = {}
TOKEN_MODIFIER_TO_INDEX = {}

for i, value in enumerate(TOKEN_TYPES):
    TOKEN_TYPE_TO_INDEX[value] = i

for i, value in enumerate(TOKEN_MODIFIERS):
    TOKEN_MODIFIER_TO_INDEX[value] = 2 ** (i + 1)  # Modifiers use a bit mask.

del i
del value


from robotframework_ls.impl.robot_constants import (
    COMMENT,
    HEADER_TOKENS,
    SETTING_TOKENS,
    NAME,
    KEYWORD_NAME,
    ARGUMENT,
    VARIABLE,
    KEYWORD,
    CONTROL_TOKENS,
    TESTCASE_NAME,
)


# See: https://code.visualstudio.com/api/language-extensions/semantic-highlight-guide#semantic-token-scope-map

RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX = {
    COMMENT: TOKEN_TYPE_TO_INDEX["comment"],
    NAME: TOKEN_TYPE_TO_INDEX["name"],
    KEYWORD_NAME: TOKEN_TYPE_TO_INDEX["keywordNameDefinition"],
    TESTCASE_NAME: TOKEN_TYPE_TO_INDEX["testCaseName"],
    KEYWORD: TOKEN_TYPE_TO_INDEX["keywordNameCall"],
    ARGUMENT: TOKEN_TYPE_TO_INDEX["parameter"],
    VARIABLE: TOKEN_TYPE_TO_INDEX["variable"],
}

for tok_type in HEADER_TOKENS:  # *** Settings ***, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["header"]
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type.replace(" ", "_")] = TOKEN_TYPE_TO_INDEX[
        "header"
    ]

for tok_type in SETTING_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["setting"]
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type.replace(" ", "_")] = TOKEN_TYPE_TO_INDEX[
        "setting"
    ]

for tok_type in CONTROL_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["control"]
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type.replace(" ", "_")] = TOKEN_TYPE_TO_INDEX[
        "control"
    ]

VARIABLE_INDEX = TOKEN_TYPE_TO_INDEX["variable"]
VARIABLE_OPERATOR_INDEX = TOKEN_TYPE_TO_INDEX["variableOperator"]
SETTING_INDEX = TOKEN_TYPE_TO_INDEX["setting"]


class _DummyToken(object):
    __slots__ = ["type", "value", "lineno", "col_offset", "end_col_offset"]

    def __init__(self):
        pass


def semantic_tokens_range(context, range):
    return []


def tokenize_variables(initial_token):
    try:
        iter_in = initial_token.tokenize_variables()
    except:
        token_type_index = RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.get(initial_token.type)
        if token_type_index is not None:
            yield initial_token, token_type_index
    else:
        for token in iter_in:

            token_type_index = RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.get(token.type)
            if token_type_index is not None:
                if (
                    token_type_index == VARIABLE_INDEX
                    and len(token.value) > 3
                    and token.value[-1] == "}"
                    and token.value[1] == "{"
                ):
                    # We want to do an additional tokenization on variables to
                    # convert '${var}' to '${', 'var', '}'
                    tok = _DummyToken()
                    tok.type = "variableOperator"
                    tok.value = token.value[:2]
                    tok.lineno = token.lineno
                    tok.col_offset = token.col_offset
                    prev_col_offset_end = tok.end_col_offset = token.col_offset + 2
                    yield tok, VARIABLE_OPERATOR_INDEX

                    tok = _DummyToken()
                    tok.type = token.type
                    tok.value = token.value[2:-1]
                    tok.lineno = token.lineno
                    tok.col_offset = prev_col_offset_end
                    prev_col_offset_end = (
                        tok.end_col_offset
                    ) = prev_col_offset_end + len(tok.value)
                    yield tok, token_type_index

                    tok = _DummyToken()
                    tok.type = "variableOperator"
                    tok.value = token.value[-1:]
                    tok.lineno = token.lineno
                    tok.col_offset = prev_col_offset_end
                    tok.end_col_offset = prev_col_offset_end + 1
                    yield tok, VARIABLE_OPERATOR_INDEX

                elif (
                    token_type_index == SETTING_INDEX
                    and len(token.value) > 2
                    and token.value[-1] == "]"
                    and token.value[0] == "["
                ):
                    # We want to do an additional tokenization on names to
                    # convert '[Arguments]' to '[', 'Arguments', ']'
                    tok = _DummyToken()
                    tok.type = "settingOperator"
                    tok.value = token.value[:1]
                    tok.lineno = token.lineno
                    tok.col_offset = token.col_offset
                    prev_col_offset_end = tok.end_col_offset = token.col_offset + 1
                    yield tok, VARIABLE_OPERATOR_INDEX

                    tok = _DummyToken()
                    tok.type = token.type
                    tok.value = token.value[1:-1]
                    tok.lineno = token.lineno
                    tok.col_offset = prev_col_offset_end
                    prev_col_offset_end = (
                        tok.end_col_offset
                    ) = prev_col_offset_end + len(tok.value)
                    yield tok, token_type_index

                    tok = _DummyToken()
                    tok.type = "settingOperator"
                    tok.value = token.value[-1:]
                    tok.lineno = token.lineno
                    tok.col_offset = prev_col_offset_end
                    tok.end_col_offset = prev_col_offset_end + 1
                    yield tok, VARIABLE_OPERATOR_INDEX

                else:
                    yield token, token_type_index


def semantic_tokens_full(context: CompletionContext):
    from robotframework_ls.impl import ast_utils

    try:
        ast = context.doc.get_ast()
    except:
        return []

    ret: List[int] = []
    append = ret.append

    last_line = 0
    last_column = 0
    for _stack, node in ast_utils._iter_nodes(ast, recursive=True):
        tokens = getattr(node, "tokens", None)
        if tokens:
            for token in tokens:
                for token_part, token_type_index in tokenize_variables(token):
                    lineno = token_part.lineno - 1
                    append(lineno - last_line)
                    if lineno != last_line:
                        last_column = token_part.col_offset
                        append(last_column)
                    else:
                        col_delta = token_part.col_offset - last_column
                        append(col_delta)
                        last_column += col_delta

                    append(token_part.end_col_offset - token_part.col_offset)  # len
                    append(token_type_index)
                    append(0)  # i.e.: no modifier
                    last_line = lineno

    return ret


def decode_semantic_tokens(
    semantic_tokens_as_int: List[int], doc: IDocument, stream=None
):
    ret: List[Tuple[str, str]] = []
    if not semantic_tokens_as_int:
        return ret

    ints_iter = iter(semantic_tokens_as_int)
    line = 0
    col = 0
    while True:
        try:
            line_delta = next(ints_iter)
        except StopIteration:
            return ret
        col_delta = next(ints_iter)
        token_len = next(ints_iter)
        token_type = next(ints_iter)
        token_modifier = next(ints_iter)
        line += line_delta
        if line_delta == 0:
            col += col_delta
        else:
            col = col_delta

        s = doc.get_line(line)[col : col + token_len]
        ret.append((s, TOKEN_TYPES[token_type]))
        if stream is not None:
            print(">>", s, "<<", file=stream)

            print(f"line: {line}", file=stream)
            print(f"col: {col}", file=stream)
            print(f"line_delta: {line_delta}", file=stream)
            print(f"col_delta: {col_delta}", file=stream)
            print(f"len: {token_len}", file=stream)
            print(f"type: {token_type}", file=stream)
            print(f"modifier: {token_modifier}", file=stream)
            print("", file=stream)
