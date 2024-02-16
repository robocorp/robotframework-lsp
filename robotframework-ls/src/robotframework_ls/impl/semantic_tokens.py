import itertools
import os
from typing import List, Tuple, Iterator, Optional, Any

from robocorp_ls_core.code_units import (
    compute_utf16_code_units_len,
    get_range_considering_utf16_code_units,
)
from robocorp_ls_core.protocols import IDocument
from robotframework_ls.impl.protocols import ICompletionContext, IRobotToken
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
    ERROR,
    FATAL_ERROR,
    ROBOT_AND_TXT_FILE_EXTENSIONS,
    OPTION,
    ASSIGN,
)
from robotframework_ls.impl.robot_localization import LocalizationInfo


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
    "error",
    "documentation",
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


def _extract_gherkin_token_from_keyword(
    scope: "_SemanticTokensScope",
    keyword_token: IRobotToken,
) -> Tuple[Optional[IRobotToken], IRobotToken]:
    from robotframework_ls.impl.ast_utils import split_token_change_first

    regexp = scope.get_gherkin_regexp()
    result = regexp.match(keyword_token.value)
    if result:
        gherkin_token_length = len(result.group(1))
        return split_token_change_first(keyword_token, "control", gherkin_token_length)

    return None, keyword_token


def _extract_library_token_from_keyword(
    keyword_token: IRobotToken, scope: "_SemanticTokensScope"
) -> Tuple[Optional[IRobotToken], IRobotToken]:
    from robotframework_ls.impl.ast_utils import split_token_change_first

    if not "." in keyword_token.value:
        return None, keyword_token

    potential_candidates = _get_potential_library_names_from_keyword(
        keyword_token.value
    )

    for library_name in potential_candidates:
        if library_name in scope.imported_libraries:
            return split_token_change_first(keyword_token, "name", len(library_name))
    return None, keyword_token


def _get_potential_library_names_from_keyword(keyword_name: str) -> Iterator[str]:
    name_length = -1
    while True:
        name_length = keyword_name.find(".", name_length + 1)
        if name_length == -1:
            break
        library_name = keyword_name[:name_length].lower()
        yield library_name


def _iter_dependent_names(context: ICompletionContext) -> Iterator[str]:
    """
    Provides names which can be used as (library/resource) prefixes
    for keyword calls.

    Note: names returned are all lower-case as case should not be taken into
    account for matches.
    """
    dependency_graph = context.collect_dependency_graph()
    for library in dependency_graph.iter_all_libraries():
        name = library.name
        if name:
            library_name = os.path.basename(name)
            basename, ext = os.path.splitext(library_name)
            if ext == ".py":
                yield basename.lower()
            else:
                yield name.lower()

        alias = library.alias
        if alias:
            yield alias.lower()

    for resource_node, _ in dependency_graph.iter_all_resource_imports_with_docs():
        name = resource_node.name
        if name:
            resource_name = os.path.basename(name)
            basename, ext = os.path.splitext(resource_name)
            if ext in ROBOT_AND_TXT_FILE_EXTENSIONS:
                yield basename.lower()
            else:
                yield name.lower()


# See: https://code.visualstudio.com/api/language-extensions/semantic-highlight-guide#semantic-token-scope-map

RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX = {
    COMMENT: TOKEN_TYPE_TO_INDEX["comment"],
    NAME: TOKEN_TYPE_TO_INDEX["name"],
    KEYWORD_NAME: TOKEN_TYPE_TO_INDEX["keywordNameDefinition"],
    TESTCASE_NAME: TOKEN_TYPE_TO_INDEX["testCaseName"],
    KEYWORD: TOKEN_TYPE_TO_INDEX["keywordNameCall"],
    ARGUMENT: TOKEN_TYPE_TO_INDEX["argumentValue"],
    VARIABLE: TOKEN_TYPE_TO_INDEX["variable"],
    ERROR: TOKEN_TYPE_TO_INDEX["error"],
    FATAL_ERROR: TOKEN_TYPE_TO_INDEX["error"],
    OPTION: TOKEN_TYPE_TO_INDEX["argumentValue"],
    # Special: we don't have a token regarding such operators in RF, so, add
    # 'variableOperator' as being valid for both.
    "variableOperator": TOKEN_TYPE_TO_INDEX["variableOperator"],
}

# INVALID HEADER was added in RF 6.1.
RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX["INVALID HEADER"] = TOKEN_TYPE_TO_INDEX["error"]

for tok_type in HEADER_TOKENS:  # *** Settings ***, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["header"]

for tok_type in SETTING_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["setting"]

for tok_type in CONTROL_TOKENS:  # Library, Teardown, ...
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[tok_type] = TOKEN_TYPE_TO_INDEX["control"]

# The assign will be tokenized and the '=' will be variableOperator.
RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[ASSIGN] = TOKEN_TYPE_TO_INDEX["variableOperator"]

for key, val in list(RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.items()):
    RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX[key.replace(" ", "_")] = val


VARIABLE_INDEX = TOKEN_TYPE_TO_INDEX["variable"]
ARGUMENT_INDEX = TOKEN_TYPE_TO_INDEX["argumentValue"]
VARIABLE_OPERATOR_INDEX = TOKEN_TYPE_TO_INDEX["variableOperator"]
SETTING_INDEX = TOKEN_TYPE_TO_INDEX["setting"]
PARAMETER_NAME_INDEX = TOKEN_TYPE_TO_INDEX["parameterName"]
DOCUMENTATION_INDEX = TOKEN_TYPE_TO_INDEX["documentation"]
CONTROL_INDEX = TOKEN_TYPE_TO_INDEX["control"]


def _tokenize_changing_argument_to_type(tokenize_variables_generator, use_type):
    from robotframework_ls.impl import ast_utils

    for tok in tokenize_variables_generator:
        if tok.type == ARGUMENT:
            yield ast_utils.copy_token_replacing(tok, type=use_type)
        else:
            yield tok


def _tokenize_variables(token: IRobotToken) -> Iterator[IRobotToken]:
    if token.type in (KEYWORD, ASSIGN):
        from robotframework_ls.impl import ast_utils

        # Hack because RF can't tokenize KEYWORD (it only tokenizes
        # some pre-defined types and KEYWORD is not there).

        if not token.value or "{" not in token.value:
            # Nothing to tokenize.
            return iter((token,))

        else:
            # Force ARGUMENT tokenization but show KEYWORD/ASSIGN for callers.
            t = ast_utils.copy_token_replacing(token, type=ARGUMENT)
            return _tokenize_changing_argument_to_type(
                t.tokenize_variables(), token.type
            )

    else:
        return token.tokenize_variables()


def semantic_tokens_range(context, range):
    return []


def _tokenize_token(
    node, use_token, scope: "_SemanticTokensScope"
) -> Iterator[Tuple[IRobotToken, int]]:
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    if use_token.type in (use_token.EOL, use_token.SEPARATOR):
        # Fast way out for the most common tokens (which have no special handling).
        return

    from robotframework_ls.impl.variable_resolve import find_split_index

    from robotframework_ls.impl.ast_utils import (
        CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET,
        copy_token_replacing,
        split_token_change_first,
        is_node_with_expression_argument,
        iter_expression_tokens,
    )

    use_token_type = use_token.type
    in_documentation = False
    token_type_index: Optional[int]

    # Step 1: cast to KEYWORD if needed.
    if use_token_type == ARGUMENT:
        in_documentation = node.__class__.__name__ == "Documentation" or (
            node.__class__.__name__ == "KeywordCall" and node.keyword == "Comment"
        )

        if not in_documentation:
            in_expression = is_node_with_expression_argument(node)
            if scope.keyword_usage_handler is not None:
                tok_type = scope.keyword_usage_handler.get_token_type(use_token)
                if tok_type == scope.keyword_usage_handler.KEYWORD:
                    use_token_type = KEYWORD

                elif tok_type == scope.keyword_usage_handler.EXPRESSION:
                    in_expression = True

                elif tok_type == scope.keyword_usage_handler.CONTROL:
                    yield use_token, CONTROL_INDEX
                    return

            if in_expression:
                for token, _var_info in iter_expression_tokens(use_token):
                    token_type_index = scope.get_index_from_rf_token_type(token.type)
                    if token_type_index is not None:
                        yield token, token_type_index
                return

    if use_token_type == NAME:
        if node.__class__.__name__ in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET:
            use_token_type = KEYWORD

    if use_token.type != use_token_type:
        use_token = copy_token_replacing(use_token, type=use_token_type)

    if use_token_type == KEYWORD:
        token_keyword = use_token

        token_gherkin_prefix, token_keyword = _extract_gherkin_token_from_keyword(
            scope, token_keyword
        )
        if token_gherkin_prefix:
            yield (
                token_gherkin_prefix,
                scope.get_index_from_internal_token_type(token_gherkin_prefix.type),
            )

        token_library_prefix, token_keyword = _extract_library_token_from_keyword(
            token_keyword, scope
        )
        if token_library_prefix:
            yield (
                token_library_prefix,
                scope.get_index_from_internal_token_type(token_library_prefix.type),
            )

        use_token = token_keyword

    try:
        iter_in = _tokenize_variables(use_token)
    except:
        if in_documentation:
            yield use_token, DOCUMENTATION_INDEX
        else:
            token_type_index = scope.get_index_from_rf_token_type(use_token_type)
            if token_type_index is not None:
                yield use_token, token_type_index
        return
    else:
        if use_token_type == ARGUMENT:
            first_token = next(iter_in)

            if in_documentation:
                equals_pos = -1
            else:
                if first_token.value == "WITH NAME":
                    value = node.get_value(use_token.KEYWORD)
                    if value and normalize_robot_name(value) == "importlibrary":
                        yield first_token, CONTROL_INDEX
                        return

                equals_pos = find_split_index(first_token.value)
                if equals_pos != -1:
                    # Found an equals... let's check if it's not a 'catenate', which
                    # doesn't really accept parameters and just concatenates all...
                    value = node.get_value(use_token.KEYWORD)
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
                tok, first_token = split_token_change_first(
                    first_token, "parameterName", equals_pos
                )
                yield tok, PARAMETER_NAME_INDEX

                tok, first_token = split_token_change_first(
                    first_token, "variableOperator", 1
                )
                yield tok, VARIABLE_OPERATOR_INDEX

                # Add the remainder back.
                iter_in = itertools.chain(iter((first_token,)), iter_in)
            else:
                iter_in = itertools.chain(iter((first_token,)), iter_in)

        for token in iter_in:
            token_type_index = scope.get_index_from_rf_token_type(token.type)
            if token_type_index is not None:
                yield from _tokenized_args(
                    token, token_type_index, in_documentation, scope
                )


def _tokenize_subvars(var_token, token_type_index, scope):
    if "{" not in var_token.value:
        yield var_token, token_type_index
        return

    from robotframework_ls.impl import ast_utils

    var_type = var_token.type
    if var_type == "variableOperator":
        var_type = var_token.VARIABLE

    for token, _var_info in ast_utils._tokenize_subvars_tokens(
        var_token, var_type=var_type
    ):
        token_type_index = scope.get_index_from_rf_token_type(token.type)
        if token_type_index is not None:
            yield token, token_type_index


def _tokenized_args(token, token_type_index, in_documentation, scope):
    from robotframework_ls.impl.ast_utils import split_token_change_first
    from robotframework_ls.impl.ast_utils import split_token_change_second
    from robotframework_ls.impl.ast_utils import split_token_in_3

    if in_documentation and token_type_index == ARGUMENT_INDEX:
        # Handle the doc itself (note that we may also tokenize docs
        # to include variables).
        yield token, DOCUMENTATION_INDEX
        return

    if token_type_index == VARIABLE_INDEX:
        from robotframework_ls.impl.variable_resolve import robot_search_variable

        variable_match = robot_search_variable(token.value)
        if variable_match is None or variable_match.base is None:
            yield token, token_type_index
            return

        after_token = None
        if variable_match.end > 0 and variable_match.end < len(token.value):
            token, after_token = split_token_change_first(
                token, token.type, variable_match.end
            )

        if variable_match.start > 0:
            before_token, token = split_token_change_first(
                token, token.type, variable_match.start
            )
            yield before_token, token_type_index

        base = variable_match.base
        if base:
            i = token.value.find(base)
        else:
            i = token.value.find("{") + 1
        op_start_token, var_token, op_end_token = split_token_in_3(
            token,
            "variableOperator",
            token.type,
            "variableOperator",
            i,
            i + len(base),
        )

        yield op_start_token, VARIABLE_OPERATOR_INDEX
        yield from _tokenize_subvars(var_token, token_type_index, scope)

        if variable_match.items:
            for item in variable_match.items:
                token = op_end_token
                i = token.value.find(item)

                op_start_token, var_token, op_end_token = split_token_in_3(
                    token,
                    "variableOperator",
                    token.type,
                    "variableOperator",
                    i,
                    i + len(item),
                )

                yield op_start_token, VARIABLE_OPERATOR_INDEX
                yield from _tokenize_subvars(var_token, token_type_index, scope)

        yield op_end_token, VARIABLE_OPERATOR_INDEX

        if after_token:
            yield after_token, token_type_index
        return

    if (
        token_type_index == SETTING_INDEX
        and len(token.value) > 2
        and token.value[-1] == "]"
        and token.value[0] == "["
    ):
        # We want to do an additional tokenization on names to
        # convert '[Arguments]' to '[', 'Arguments', ']'
        op_start_token, token = split_token_change_first(token, "settingOperator", 1)
        yield op_start_token, VARIABLE_OPERATOR_INDEX

        var_token, op_end_token = split_token_change_second(
            token, "settingOperator", len(token.value) - 1
        )
        yield var_token, token_type_index
        yield op_end_token, VARIABLE_OPERATOR_INDEX

        return

    if token.type == OPTION:
        eq_i = token.value.index("=")
        if eq_i != -1:
            # Convert limit=10 to 'limit' '=' '10'
            var_start_token, token = split_token_change_first(
                token, "parameterName", eq_i
            )
            yield var_start_token, PARAMETER_NAME_INDEX

            var_token, var_end_token = split_token_change_second(
                token, "variableOperator", 1
            )
            yield var_token, VARIABLE_OPERATOR_INDEX
            yield var_end_token, ARGUMENT_INDEX
            return

    # Default case (just yield the current token/type).
    yield token, token_type_index


class _SemanticTokensScope:
    def __init__(
        self, context: ICompletionContext, localization_info: LocalizationInfo
    ):
        import re

        # It's the same for all files.
        self.imported_libraries = set(_iter_dependent_names(context))
        self.localization_info = localization_info

        # Note: it's set for the node and then reused for all the tokens in that same node.
        self.keyword_usage_handler: Any = None

        self.get_index_from_rf_token_type = RF_TOKEN_TYPE_TO_TOKEN_TYPE_INDEX.get
        self.get_index_from_internal_token_type = TOKEN_TYPE_TO_INDEX.__getitem__

        regexp = ["^(("]
        for prefix in localization_info.iter_bdd_prefixes_on_read():
            if len(regexp) > 1:
                regexp.append("|")
            regexp.append(re.escape(prefix))
        regexp.append(")\s+)")

        self._gherkin_regexp = re.compile("".join(regexp), flags=re.IGNORECASE)

    def get_gherkin_regexp(self):
        "^((Given|When|Then|And|But)\s+)"
        return self._gherkin_regexp


def semantic_tokens_full(context: ICompletionContext):
    from robotframework_ls.impl import ast_utils_keyword_usage
    from robotframework_ls.impl.ast_utils import get_localization_info_from_model

    try:
        ast = context.doc.get_ast()
    except:
        return []

    from robotframework_ls.impl import ast_utils

    monitor = context.monitor

    ret: List[int] = []
    append = ret.append

    last_line = 0
    last_column = 0

    localization_info = get_localization_info_from_model(ast)

    scope = _SemanticTokensScope(context, localization_info)
    for stack, node in ast_utils.iter_all_nodes_recursive(ast):
        if monitor:
            monitor.check_cancelled()
        tokens = getattr(node, "tokens", None)
        if tokens:
            scope.keyword_usage_handler = (
                ast_utils_keyword_usage.obtain_keyword_usage_handler(stack, node)
            )
            diff_in_line = 0

            for token in tokens:
                for token_part, token_type_index in _tokenize_token(node, token, scope):
                    lineno = token_part.lineno - 1
                    if lineno < 0:
                        lineno = 0
                    append(lineno - last_line)
                    if lineno != last_line:
                        diff_in_line = 0
                        last_column = token_part.col_offset
                        if last_column < 0:
                            last_column = 0
                        append(last_column)
                    else:
                        col_delta = token_part.col_offset + diff_in_line - last_column
                        append(col_delta)
                        last_column += col_delta

                    len_unicode = len(token_part.value)
                    len_bytes = compute_utf16_code_units_len(token_part.value)
                    append(len_bytes)
                    diff_in_line += len_bytes - len_unicode
                    append(token_type_index)
                    append(0)  # i.e.: no modifier
                    last_line = lineno

    return ret


def iter_decoded_semantic_tokens(semantic_tokens_as_int: List[int]):
    if not semantic_tokens_as_int:
        return

    ints_iter = iter(semantic_tokens_as_int)
    line = 0
    col = 0
    while True:
        try:
            line_delta = next(ints_iter)
        except StopIteration:
            return
        col_delta = next(ints_iter)
        token_len = next(ints_iter)
        token_type = next(ints_iter)
        token_modifier = next(ints_iter)
        line += line_delta
        if line_delta == 0:
            col += col_delta
        else:
            col = col_delta

        yield {
            "line": line,
            "col": col,
            "line_delta": line_delta,
            "col_delta": col_delta,
            "len": token_len,
            "type": token_type,
            "modifier": token_modifier,
        }


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

        # s = doc.get_line(line)[col : col + token_len]
        s = doc.get_line(line)
        s = get_range_considering_utf16_code_units(s, col, col + token_len)

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
