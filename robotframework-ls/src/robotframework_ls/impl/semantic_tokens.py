from typing import List, Tuple, Optional
import itertools
from robocorp_ls_core.protocols import IDocument, IMonitor
from robotframework_ls.impl.protocols import ICompletionContext


TOKEN_TYPES = [
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
    "parameterName",
    "argumentValue",
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
    ARGUMENT: TOKEN_TYPE_TO_INDEX["argumentValue"],
    VARIABLE: TOKEN_TYPE_TO_INDEX["variable"],
}


for tok_type in HEADER_TOKENS:  # *** Settings ***, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["header"]

for tok_type in SETTING_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["setting"]

for tok_type in CONTROL_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["control"]

for key, val in list(RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.items()):
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[key.replace(" ", "_")] = val


VARIABLE_INDEX = TOKEN_TYPE_TO_INDEX["variable"]
VARIABLE_OPERATOR_INDEX = TOKEN_TYPE_TO_INDEX["variableOperator"]
SETTING_INDEX = TOKEN_TYPE_TO_INDEX["setting"]
PARAMETER_NAME_INDEX = TOKEN_TYPE_TO_INDEX["parameterName"]


class _DummyToken(object):
    __slots__ = ["type", "value", "lineno", "col_offset", "end_col_offset"]

    def __init__(self):
        pass


def semantic_tokens_range(context, range):
    return []


def _tokenize_token(node, initial_token):
    from robotframework_ls.impl.ast_utils import is_argument_keyword_name

    if initial_token.type == ARGUMENT:
        if is_argument_keyword_name(node, initial_token):
            token_type_index = RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[KEYWORD]
            yield initial_token, token_type_index
            return

    try:
        iter_in = initial_token.tokenize_variables()
    except:
        token_type = initial_token.type

        token_type_index = RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.get(token_type)
        if token_type_index is not None:
            yield initial_token, token_type_index
    else:
        if (
            initial_token.type == ARGUMENT
            and node.__class__.__name__ != "Documentation"
        ):

            first_token = next(iter_in)
            equals_pos = first_token.value.find("=")
            if equals_pos != -1:
                # Found an equals... let's check if it's not a 'catenate', which
                # doesn't really accept parameters and just concatenates all...
                value = node.get_value(initial_token.KEYWORD)
                if value and value.strip().lower() == "catenate":
                    equals_pos = -1

                    # Note: the best way to actually do this would be finding the
                    # reference to the keyword and then validating whether the
                    # keyword arguments match the expected name.
                    #
                    # For instance, a keyword call such as:
                    # Some Call     some arg = 22
                    #
                    # Should color `some arg =` differently only if the argument
                    # of `Some Call` is `some arg`, otherwise it should not color
                    # the argument as `same arg = 22` will be passed as a string
                    # to the positional argument 0 and not really a keyword parameter
                    # where `same arg` is set with value 22.
                    #
                    # Now, this requires a bit more tinkering with keyword caches
                    # and possibly semantic highlighting deltas to make sure the
                    # performance isn't negatively impacted by it.

            if equals_pos != -1:
                tok = _DummyToken()
                tok.type = "parameterName"
                tok.value = first_token.value[:equals_pos]
                tok.lineno = first_token.lineno
                tok.col_offset = first_token.col_offset
                prev_col_offset_end = tok.end_col_offset = first_token.col_offset + len(
                    tok.value
                )
                yield tok, PARAMETER_NAME_INDEX

                tok = _DummyToken()
                tok.type = "variableOperator"
                tok.value = "="
                tok.lineno = first_token.lineno
                tok.col_offset = prev_col_offset_end
                prev_col_offset_end = tok.end_col_offset = prev_col_offset_end + 1
                yield tok, VARIABLE_OPERATOR_INDEX

                # Add the remainder back.
                first_token_remainder = _DummyToken()
                first_token_remainder.type = first_token.type
                first_token_remainder.value = first_token.value[equals_pos + 1 :]
                first_token_remainder.lineno = first_token.lineno
                first_token_remainder.col_offset = prev_col_offset_end
                prev_col_offset_end = (
                    first_token_remainder.end_col_offset
                ) = prev_col_offset_end + len(first_token_remainder.value)

                iter_in = itertools.chain(iter([first_token_remainder]), iter_in)
            else:
                iter_in = itertools.chain(iter((first_token,)), iter_in)

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


def semantic_tokens_full(context: ICompletionContext):
    try:
        ast = context.doc.get_ast()
    except:
        return []
    return semantic_tokens_full_from_ast(ast, context.monitor)


def semantic_tokens_full_from_ast(ast, monitor: Optional[IMonitor]):
    from robotframework_ls.impl import ast_utils

    ret: List[int] = []
    append = ret.append

    last_line = 0
    last_column = 0
    for _stack, node in ast_utils._iter_nodes(ast, recursive=True):
        if monitor:
            monitor.check_cancelled()
        tokens = getattr(node, "tokens", None)
        if tokens:
            for token in tokens:
                for token_part, token_type_index in _tokenize_token(node, token):
                    lineno = token_part.lineno - 1
                    if lineno < 0:
                        lineno = 0
                    append(lineno - last_line)
                    if lineno != last_line:
                        last_column = token_part.col_offset
                        if last_column < 0:
                            last_column = 0
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
