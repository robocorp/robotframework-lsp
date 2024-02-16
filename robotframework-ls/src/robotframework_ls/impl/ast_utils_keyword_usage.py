from typing import Optional, Iterator, Tuple

from robotframework_ls.impl.protocols import KeywordUsageInfo, IRobotToken
from robotframework_ls.impl.keywords_in_args import KEYWORD_NAME_TO_KEYWORD_INDEX
from robotframework_ls.impl.keywords_in_args import KEYWORD_NAME_TO_CONDITION_INDEX

TOK_TYPE_NONE = 0
TOK_TYPE_KEYWORD = 1
TOK_TYPE_EXPRESSION = 2
TOK_TYPE_CONTROL = 3
TOK_TYPE_IGNORE = 4


def _tok_type_as_str(tok_type) -> str:
    if tok_type == TOK_TYPE_NONE:
        return "<none>"
    if tok_type == TOK_TYPE_EXPRESSION:
        return "<expression>"
    if tok_type == TOK_TYPE_KEYWORD:
        return "<keyword>"
    if tok_type == TOK_TYPE_CONTROL:
        return "<control>"
    if tok_type == TOK_TYPE_IGNORE:
        return "<ignore>"
    raise AssertionError(f"Unexpected: {tok_type}")


class _ConsiderArgsAsKeywordNames:
    NONE = TOK_TYPE_NONE
    KEYWORD = TOK_TYPE_KEYWORD
    EXPRESSION = TOK_TYPE_EXPRESSION
    CONTROL = TOK_TYPE_CONTROL
    IGNORE = TOK_TYPE_IGNORE

    def __init__(
        self,
        node,
        normalized_keyword_name,
        consider_keyword_at_index,
        consider_condition_at_index,
    ):
        self._normalized_keyword_name = normalized_keyword_name
        self._consider_keyword_at_index = consider_keyword_at_index
        self._consider_condition_at_index = consider_condition_at_index
        self._current_arg = 0

        # Run Keyword If is special because it has 'ELSE IF' / 'ELSE'
        # which will then be be (cond, keyword) or just (keyword), so
        # we need to provide keyword usages as needed.
        if self._normalized_keyword_name == "runkeywordif":
            self.next_tok_type = self._next_tok_type_run_keyword_if
        elif self._normalized_keyword_name == "foreachinputworkitem":
            self.next_tok_type = self._next_tok_type_for_each_input_work_item
        elif self._normalized_keyword_name == "runkeywords":
            found = False
            for token in node.tokens:
                if "AND" == token.value:
                    found = True
                    break
            if found:
                self.next_tok_type = self._next_tok_type_run_keywords
            else:
                self.next_tok_type = self._consider_each_arg_as_keyword

        self._stack_kind = None
        self._stack = None
        self._started_match = False

    def next_tok_type(self, token) -> int:  # pylint: disable=method-hidden
        assert token.type == token.ARGUMENT
        self._current_arg += 1

        if self._current_arg == self._consider_condition_at_index:
            return self.EXPRESSION

        if self._current_arg == self._consider_keyword_at_index:
            return self.KEYWORD

        return self.NONE

    def _next_tok_type_for_each_input_work_item(self, token):
        from robotframework_ls.impl.variable_resolve import find_split_index
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        assert token.type == token.ARGUMENT
        self._current_arg += 1

        if self._current_arg == self._consider_keyword_at_index:
            return self.KEYWORD

        i = find_split_index(token.value)
        if i > 0:
            v = normalize_robot_name(token.value[:i])
            if v in ("itemslimit", "returnresults"):
                return self.IGNORE

        return self.NONE

    def _next_tok_type_run_keyword_if(self, token):
        assert token.type == token.ARGUMENT

        self._current_arg += 1

        if token.value == "ELSE IF":
            self._started_match = True
            self._stack = []
            self._stack_kind = token.value
            return self.CONTROL
        elif token.value == "ELSE":
            self._started_match = True
            self._stack = []
            self._stack_kind = token.value
            return self.CONTROL

        else:
            self._started_match = False
            if self._stack is not None:
                self._stack.append(token)

        if self._stack is not None:
            if self._stack_kind == "ELSE IF":
                if len(self._stack) == 1:
                    return self.EXPRESSION
                return self.KEYWORD if len(self._stack) == 2 else self.NONE

            if self._stack_kind == "ELSE":
                return self.KEYWORD if len(self._stack) == 1 else self.NONE

        if self._current_arg == self._consider_condition_at_index:
            return self.EXPRESSION

        if self._current_arg == self._consider_keyword_at_index:
            return self.KEYWORD

        return self.NONE

    def _consider_each_arg_as_keyword(self, token):
        assert token.type == token.ARGUMENT
        return self.KEYWORD

    def _next_tok_type_run_keywords(self, token):
        assert token.type == token.ARGUMENT

        self._current_arg += 1

        if token.value == "AND":
            self._started_match = True
            self._stack = []
            self._stack_kind = token.value
            return self.CONTROL

        else:
            self._started_match = False
            if self._stack is not None:
                self._stack.append(token)

        if self._stack is not None:
            if self._stack_kind == "AND":
                return self.KEYWORD if len(self._stack) == 1 else self.NONE

        if self._current_arg == self._consider_keyword_at_index:
            return self.KEYWORD
        return self.NONE


def _create_root_keyword_usage_info(stack, node) -> Optional[KeywordUsageInfo]:
    """
    If this is a keyword usage node, return information on it, otherwise,
    returns None.

    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    from robot.api import Token
    from robotframework_ls.impl.ast_utils import (
        CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET,
    )
    from robotframework_ls.impl.ast_utils import _strip_node_and_token_bdd_prefix

    if node.__class__.__name__ == "KeywordCall":
        token_type = Token.KEYWORD

    elif node.__class__.__name__ in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET:
        token_type = Token.NAME

    else:
        return None

    prefix, node, token = _strip_node_and_token_bdd_prefix(stack, node, token_type)
    if token is None:
        return None

    keyword_name = token.value
    if keyword_name.lower() == "none":
        return None
    return KeywordUsageInfo(tuple(stack), node, token, keyword_name, prefix=prefix)


def _build_keyword_usage(stack, node, current_tokens) -> Optional[KeywordUsageInfo]:
    from robotframework_ls.impl.ast_utils import copy_token_replacing

    # Note: just check for line/col because the token could be changed
    # (for instance, an EOL ' ' could be added to the token).
    if not current_tokens:
        return None

    keyword_at_index = 0
    keyword_token = current_tokens[keyword_at_index]

    keyword_token = copy_token_replacing(keyword_token, type=keyword_token.KEYWORD)
    new_tokens = [keyword_token]
    new_tokens.extend(current_tokens[keyword_at_index + 1 :])

    new_node = node.__class__(new_tokens)
    return KeywordUsageInfo(
        stack,
        new_node,
        keyword_token,
        keyword_token.value,
        True,
    )


def _iter_keyword_usage_info_uncached_from_args(
    stack, node, args_as_keywords_handler, token_line_col_to_type
) -> Iterator[KeywordUsageInfo]:
    # We may have multiple matches, so, we need to setup the appropriate book-keeping
    current_tokens = []

    iter_in = iter(node.tokens)

    for token in iter_in:
        if token.type == token.ARGUMENT:
            next_tok_type = args_as_keywords_handler.next_tok_type(token)
            token_line_col_to_type[(token.lineno, token.col_offset)] = next_tok_type
            if next_tok_type == args_as_keywords_handler.KEYWORD:
                current_tokens.append(token)
                break

    for token in iter_in:
        if token.type == token.ARGUMENT:
            next_tok_type = args_as_keywords_handler.next_tok_type(token)
            token_line_col_to_type[(token.lineno, token.col_offset)] = next_tok_type

            if next_tok_type in (
                args_as_keywords_handler.CONTROL,
                args_as_keywords_handler.EXPRESSION,
                args_as_keywords_handler.IGNORE,
            ):
                # Don't add IF/ELSE IF/AND nor the condition.
                continue

            if next_tok_type != args_as_keywords_handler.KEYWORD:
                # Argument was now added to current_tokens.
                current_tokens.append(token)
                continue

            if current_tokens:
                # Starting a new one (build for the previous).
                usage_info = _build_keyword_usage(
                    stack,
                    node,
                    current_tokens,
                )
                if usage_info is not None:
                    yield usage_info

            current_tokens = [token]

    else:
        # Do one last iteration at the end to deal with the last one.
        if current_tokens:
            usage_info = _build_keyword_usage(
                stack,
                node,
                current_tokens,
            )
            if usage_info is not None:
                yield usage_info


class _KeywordUsageHandler:
    """
    We have the following main use-cases when dealing with keyword usages (also
    known as keyword references):

    1. Obtain the usages (keyword call/arguments) for code-analysis.
    2. For each token in a keyword usage, know what it maps to (
       keyword name, expression, control, regular argument, ...)

    Also, it needs to be considered that a given keyword usage may have
    other usages within it, so, the _KeywordUsageHandler is an API to help
    make things more streamlined for each use-case.
    """

    NONE = TOK_TYPE_NONE
    KEYWORD = TOK_TYPE_KEYWORD
    EXPRESSION = TOK_TYPE_EXPRESSION
    CONTROL = TOK_TYPE_CONTROL
    IGNORE = TOK_TYPE_IGNORE

    def __init__(self, stack, node, recursive):
        self.node = node
        self.stack = stack
        self._recursive = recursive

        # We store as line/col the type info and not the actual token because we
        # may create dummy tokens along the way and in this case we're
        # interested in the positions.
        self._token_line_col_to_type = {}
        self._keyword_usages_from_node_cache = None

    def _ensure_cached(self):
        if self._keyword_usages_from_node_cache is None:
            self._keyword_usages_from_node_cache = tuple(
                self._iter_keyword_usages_from_node()
            )

    def iter_keyword_usages_from_node(self) -> Iterator[KeywordUsageInfo]:
        self._ensure_cached()
        yield from iter(self._keyword_usages_from_node_cache)

    def _iter_keyword_usages_from_node(self) -> Iterator[KeywordUsageInfo]:
        """
        Note: the iteration order is guaranteed and it's from the inside to
        the outside (because when matching tokens we want to match more
        specific ones before outer ones).
        """

        root_keyword_usage_info = _create_root_keyword_usage_info(self.stack, self.node)
        if root_keyword_usage_info is None:
            return

        # Ok, we have the root one, now, we need to recursively detect others.
        if self._recursive:
            yield from self._iter_keyword_usages_inside_keyword_usage(
                root_keyword_usage_info
            )

        yield root_keyword_usage_info

    def _iter_keyword_usages_inside_keyword_usage(
        self, root_keyword_usage_info: KeywordUsageInfo
    ) -> Iterator[KeywordUsageInfo]:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        # Now, we have the root, determine if it can have other usages inside itself...
        normalized_keyword_name = normalize_robot_name(root_keyword_usage_info.name)
        consider_keyword_at_index = KEYWORD_NAME_TO_KEYWORD_INDEX.get(
            normalized_keyword_name
        )
        consider_condition_at_index = KEYWORD_NAME_TO_CONDITION_INDEX.get(
            normalized_keyword_name
        )
        if (
            consider_keyword_at_index is not None
            or consider_condition_at_index is not None
        ):
            args_as_keywords_handler = _ConsiderArgsAsKeywordNames(
                root_keyword_usage_info.node,
                normalized_keyword_name,
                consider_keyword_at_index,
                consider_condition_at_index,
            )

            for kw_usage in _iter_keyword_usage_info_uncached_from_args(
                self.stack,
                root_keyword_usage_info.node,
                args_as_keywords_handler,
                self._token_line_col_to_type,
            ):
                yield from self._iter_keyword_usages_inside_keyword_usage(kw_usage)
                yield kw_usage

    def get_token_type(self, tok: IRobotToken) -> int:
        """
        :return:
            TOK_TYPE_NONE = 0
            TOK_TYPE_KEYWORD = 1
            TOK_TYPE_EXPRESSION = 2
            TOK_TYPE_CONTROL = 3
            TOK_TYPE_IGNORE = 4
        """
        self._ensure_cached()
        return self._token_line_col_to_type.get(
            (tok.lineno, tok.col_offset), TOK_TYPE_NONE
        )

    def get_token_type_as_str(self, token: IRobotToken) -> str:
        return _tok_type_as_str(self.get_token_type(token))

    def iter_tokens_with_type(self) -> Iterator[Tuple[IRobotToken, int]]:
        self._ensure_cached()
        for tok in self.node.tokens:
            yield (
                tok,
                self._token_line_col_to_type.get(
                    (tok.lineno, tok.col_offset), TOK_TYPE_NONE
                ),
            )

    def get_keyword_usage_for_token_line_col(
        self, line, col
    ) -> Optional[KeywordUsageInfo]:
        self._ensure_cached()
        for kw_usage in self.iter_keyword_usages_from_node():
            for token in kw_usage.node.tokens:
                if token.lineno == line and token.col_offset == col:
                    return kw_usage
        return None


def obtain_keyword_usage_handler(
    stack, node, recursive=True
) -> Optional[_KeywordUsageHandler]:
    from robotframework_ls.impl.ast_utils import (
        CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET,
    )

    if (
        node.__class__.__name__ != "KeywordCall"
        and node.__class__.__name__
        not in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET
    ):
        return None

    return _KeywordUsageHandler(stack, node, recursive=recursive)


def obtain_keyword_usage_for_token(stack, node, token) -> Optional[KeywordUsageInfo]:
    keyword_usage_handler = obtain_keyword_usage_handler(stack, node)
    if keyword_usage_handler is not None:
        keyword_usage = keyword_usage_handler.get_keyword_usage_for_token_line_col(
            token.lineno, token.col_offset
        )
        return keyword_usage
    return None
