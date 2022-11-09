from robotframework_ls.impl.protocols import (
    IKeywordArg,
    IRobotToken,
    IKeywordFound,
)
from typing import Optional, List, Deque, Iterator, Dict, Union, Sequence
import itertools
from robocorp_ls_core.lsp import Error, ICustomDiagnosticDataUnexpectedArgumentTypedDict
from robocorp_ls_core.constants import Null, NULL
import typing


class _Match:
    def __init__(
        self, definition_arg: IKeywordArg, token_definition_id_to_index: Dict[int, int]
    ):
        self._definition_arg = definition_arg
        self._token_definition_id_to_index = token_definition_id_to_index

    def get_active_parameter_in_definition(self):
        return self._token_definition_id_to_index.get(id(self._definition_arg), -1)


class SkipAnalysisControlFlowException(Exception):
    pass


class UsageInfoForKeywordArgumentAnalysis:
    def __init__(self, node, token_to_report_missing_argument, argument_tokens=None):
        self.node = node
        self._token_to_report_missing_argument = token_to_report_missing_argument
        if argument_tokens is None:
            argument_tokens = self.node.tokens
        self.argument_tokens = argument_tokens

    def get_token_to_report_argument_missing(self):
        return self._token_to_report_missing_argument


class KeywordArgumentAnalysis:
    def __init__(
        self,
        keyword_args: Sequence[IKeywordArg],
        keyword_found: Optional[IKeywordFound] = None,
    ) -> None:
        """
        :param keyword_found:
            May be None if we're analyzing args for something as a library constructor
            (or some other case which doesn't map to a keyword).
        """

        args = self._keyword_args = keyword_args

        self.found_star_arg: Optional[IKeywordArg] = None
        self.found_keyword_arg: Optional[IKeywordArg] = None
        self.keyword_found: Optional[IKeywordFound] = keyword_found
        self._star_arg_index = -1
        self._keyword_arg_index = -1

        for i, arg in enumerate(args):
            if arg.is_star_arg:
                self.found_star_arg = arg
                self._star_arg_index = i

            elif arg.is_keyword_arg:
                self.found_keyword_arg = arg
                self._keyword_arg_index = i

    def _compute_active_parameter_fallback(
        self,
        usage_info_argument_index: int,
        usage_info_arg_tokens: Sequence[IRobotToken],
    ) -> int:
        """
        If we didn't have an exact match (because the current call would
        probably be inconsistent as the user may be typing it), provide a
        fallback which works better is such situations.
        """
        from robotframework_ls.impl.text_utilities import is_variable_text
        from robotframework_ls.impl.variable_resolve import find_split_index

        if usage_info_argument_index < 0:
            return -1

        if usage_info_argument_index >= len(usage_info_arg_tokens):
            # This happens when the user is starting to type an argument.
            return usage_info_argument_index

        active_parameter: int = usage_info_argument_index
        if self._keyword_arg_index == -1 and self._star_arg_index >= 0:
            if active_parameter >= self._star_arg_index:
                return self._star_arg_index

        caller_arg_value = usage_info_arg_tokens[active_parameter].value
        definition_keyword_args = self._keyword_args
        # Now, it's also possible that we're dealing with an assign here... let's
        # see if this is the case.
        eq: int = find_split_index(caller_arg_value)
        if eq != -1:
            name = caller_arg_value[:eq]
            for i, keyword_arg in enumerate(definition_keyword_args):
                arg_name = keyword_arg.original_arg
                if is_variable_text(arg_name):
                    arg_name = arg_name[2:-1]
                arg_name = arg_name
                if name == arg_name:
                    active_parameter = i
                    break
            else:
                # We do NOT have a match (match keyword arg / star arg if present...)
                if self._keyword_arg_index >= 0:
                    active_parameter = self._keyword_arg_index

                elif self._star_arg_index >= 0:
                    active_parameter = self._star_arg_index

                else:
                    # This is actually off (error in call).
                    active_parameter = -1

        else:
            saw_eq: bool = False
            for arg in usage_info_arg_tokens[:active_parameter]:
                saw_eq = "=" in arg.value
                if saw_eq:
                    break

            if saw_eq and self._keyword_arg_index >= 0:
                return self._keyword_arg_index

            # Ok, does not have an assign, let's inspect the original signature
            # to detect where this should be put there (positional arg or
            # stararg).
            for i, definition_arg in enumerate(definition_keyword_args):
                if i == active_parameter:
                    break

                if definition_arg.is_star_arg:
                    active_parameter = i
                    break

                if definition_arg.is_keyword_arg:
                    # This is actually off (error in call).
                    active_parameter = -1
                    break

        return active_parameter

    def _iter_args(self, tokens):
        from robot.api import Token

        for token in tokens:
            if token.type == Token.ARGUMENT:
                if token.value.startswith("&{") or token.value.startswith("@{"):
                    # All bets are off in this case (it may match anything...)
                    raise SkipAnalysisControlFlowException()

                yield token

    def _collect_keyword_usage_errors_and_build_definition_map(
        self,
        usage_info: UsageInfoForKeywordArgumentAnalysis,
        usage_token_id_to_definition_arg_match: Union[Dict[int, _Match], Null] = NULL,
        collect_errors=True,
    ) -> Iterator[Error]:
        try:
            yield from self._collect_keyword_usage_errors_and_build_definition_map_raises_exc(
                usage_info, usage_token_id_to_definition_arg_match, collect_errors
            )
        except SkipAnalysisControlFlowException:
            pass

    def _create_unexpected_arg_data(self, arg_name: str):
        keyword_found = self.keyword_found
        if keyword_found is None:
            return None
        ast = keyword_found.keyword_ast
        if ast is None:
            return None

        if keyword_found.source is None:
            return None

        if not keyword_found.keyword_name:
            return None

        # Only create the data if we have a reference to the ast (where it's
        # actionable afterwards to create an argument through code actions).
        unexpected_arg_data: ICustomDiagnosticDataUnexpectedArgumentTypedDict = {
            "kind": "unexpected_argument",
            "arg_name": arg_name,
            "keyword_name": keyword_found.keyword_name,
            "path": keyword_found.source,
        }
        return unexpected_arg_data

    def _collect_keyword_usage_errors_and_build_definition_map_raises_exc(
        self,
        usage_info: UsageInfoForKeywordArgumentAnalysis,
        usage_token_id_to_definition_arg_match: Union[Dict[int, _Match], Null] = NULL,
        collect_errors=True,
    ) -> Iterator[Error]:
        """
        In this function we build the contents of usage_token_id_to_definition_arg_match
        and collect the errors (if collect_errors=True).
        """
        from robotframework_ls.impl.ast_utils import create_error_from_node
        from collections import deque
        from robotframework_ls.impl.text_utilities import is_variable_text
        from robotframework_ls.impl.variable_resolve import find_split_index
        from robotframework_ls.impl.variable_resolve import has_variable

        # Pre-requisite.
        keyword_token = usage_info.get_token_to_report_argument_missing()
        if not keyword_token:
            return

        # deque (initially with all args -- args we match are removed
        # as we go forward).
        definition_keyword_args_deque: Deque[IKeywordArg] = deque()

        # id(arg) -> index in the definition.
        token_definition_id_to_index: Dict[int, int] = {}

        # Contains all names we can match -> the related keyword arg.
        definition_keyword_name_to_arg: Dict[str, IKeywordArg] = {}

        # The ones that are matched are filled as we go.
        definition_arg_matched: Dict[IKeywordArg, bool] = {}

        # Fill our basic structures.
        for i, definition_arg in enumerate(self._keyword_args):
            definition_keyword_args_deque.append(definition_arg)
            token_definition_id_to_index[id(definition_arg)] = i

            if definition_arg.is_star_arg:
                # Skip not matched by name
                continue
            if definition_arg.is_keyword_arg:
                # Skip not matched by name
                continue

            arg_name = definition_arg.arg_name
            if is_variable_text(arg_name):
                arg_name = arg_name[2:-1]

            definition_keyword_name_to_arg[arg_name] = definition_arg

        # The keys from definition_keyword_name_to_arg but without mutating
        # it during the analysis.
        all_definition_keyword_names: typing.FrozenSet[str] = frozenset(
            definition_keyword_name_to_arg.keys()
        )

        tokens_args_to_iterate = self._iter_args(usage_info.argument_tokens)
        # Fill positional args
        for token_arg in tokens_args_to_iterate:
            if not definition_keyword_args_deque:
                # No more arguments to consume...
                # Add it back as it still wasn't consumed (this is an error).
                tokens_args_to_iterate = itertools.chain(
                    iter([token_arg]), tokens_args_to_iterate
                )
                break

            eq_index = find_split_index(token_arg.value)

            if eq_index == -1:
                matched_keyword_arg: IKeywordArg = (
                    definition_keyword_args_deque.popleft()
                )
                if matched_keyword_arg.is_star_arg:
                    # Add star arg back as we may keep on matching it.
                    definition_keyword_args_deque.appendleft(matched_keyword_arg)
                    usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                        matched_keyword_arg, token_definition_id_to_index
                    )
                    continue

                if matched_keyword_arg.is_keyword_arg:
                    if collect_errors:
                        error = create_error_from_node(
                            usage_info.node,
                            f"Unexpected positional argument: {token_arg.value}",
                            tokens=[token_arg],
                        )
                        yield error

                    # Add it (just because the user may be typing it...)
                    usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                        matched_keyword_arg, token_definition_id_to_index
                    )

                    # Finish as it's inconsistent now.
                    return

                definition_arg_matched[matched_keyword_arg] = True
                usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                    matched_keyword_arg, token_definition_id_to_index
                )

            else:
                if self.found_keyword_arg is not None:
                    # Something with '=' always matches keyword args, even if
                    # no named args would be matched. Add it back to go to
                    # the part where we match arguments by name.
                    tokens_args_to_iterate = itertools.chain(
                        iter([token_arg]), tokens_args_to_iterate
                    )
                    break

                name = token_arg.value[:eq_index]

                if has_variable(name):
                    # If an argument has variables, skip the analysis.
                    return

                found_definition_arg = definition_keyword_name_to_arg.get(name, None)
                if found_definition_arg is not None:
                    if definition_arg_matched.get(found_definition_arg):
                        error = create_error_from_node(
                            usage_info.node,
                            f"Multiple values for argument: {name}",
                            tokens=[token_arg],
                        )
                        yield error
                        return

                    # First with eq (named argument) that matched something. Add
                    # it back to go to the part where we match arguments by name.
                    tokens_args_to_iterate = itertools.chain(
                        iter([token_arg]), tokens_args_to_iterate
                    )
                    break

                matched_keyword_arg = definition_keyword_args_deque[0]
                usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                    matched_keyword_arg, token_definition_id_to_index
                )

                if matched_keyword_arg.is_star_arg:
                    # Special-case, if the last thing we have is a star-arg, it'll
                    # consume everything (even equals) as long as no named arguments
                    # were matched first.
                    pass
                else:
                    # Matched some argument (the '=' became a part of the value).
                    definition_arg_matched[matched_keyword_arg] = True
                    definition_keyword_args_deque.popleft()

        if not definition_keyword_args_deque:
            if collect_errors:
                # If we have no more args to consume, everything else is an error.
                for token_arg in tokens_args_to_iterate:
                    if collect_errors:
                        error = create_error_from_node(
                            usage_info.node,
                            f"Unexpected argument: {token_arg.value}",
                            tokens=[token_arg],
                        )
                        error.data = self._create_unexpected_arg_data(token_arg.value)
                        yield error
            return

        # Ok, from this point onwards we need to match only by name / stararg / keyword_token arg

        # Now, consume all the ones given by name.
        for token_arg in tokens_args_to_iterate:
            eq_index = find_split_index(token_arg.value)
            if eq_index >= 0:
                name = token_arg.value[:eq_index]
                if has_variable(name):
                    # If an argument has variables, skip the analysis.
                    return

                found_definition_arg = definition_keyword_name_to_arg.pop(name, None)
                if not found_definition_arg:
                    if self.found_keyword_arg is not None:
                        usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                            self.found_keyword_arg, token_definition_id_to_index
                        )
                    else:
                        if collect_errors:
                            if name in all_definition_keyword_names:
                                error = create_error_from_node(
                                    usage_info.node,
                                    f"Argument already specified previously: {name}",
                                    tokens=[token_arg],
                                )
                                yield error
                            else:
                                error = create_error_from_node(
                                    usage_info.node,
                                    f"Unexpected named argument: {name}",
                                    tokens=[token_arg],
                                )
                                error.data = self._create_unexpected_arg_data(
                                    name + "="
                                )
                                yield error

                else:
                    usage_token_id_to_definition_arg_match[id(token_arg)] = _Match(
                        found_definition_arg, token_definition_id_to_index
                    )

            else:
                if collect_errors:
                    error = create_error_from_node(
                        usage_info.node,
                        f"Positional argument not allowed after named arguments: {token_arg.value}",
                        tokens=[token_arg],
                    )
                    yield error
                return

        if collect_errors:
            # To finish, give errors on unmatched arguments.
            for (
                definition_name,
                definition_arg,
            ) in definition_keyword_name_to_arg.items():
                if (
                    not definition_arg.is_default_value_set()
                    and not definition_arg_matched.get(definition_arg)
                ):
                    error = create_error_from_node(
                        usage_info.node,
                        f"Mandatory argument missing: {definition_name}",
                        tokens=[keyword_token],
                    )
                    yield error

    # --------------------------------------------------------------- Public API

    def compute_active_parameter(
        self, usage_info: UsageInfoForKeywordArgumentAnalysis, lineno: int, col: int
    ) -> int:

        token_to_report_argument_missing = (
            usage_info.get_token_to_report_argument_missing()
        )
        if token_to_report_argument_missing.lineno - 1 > lineno or (
            token_to_report_argument_missing.lineno - 1 == lineno
            and token_to_report_argument_missing.end_col_offset >= col
        ):
            return -1

        from robot.api import Token

        usage_info_argument_index: int = 0
        # We need to find out the current arg/separator.
        after_last_arg: List[Token] = []
        usage_info_arg_tokens: List[Token] = []

        for token in usage_info.argument_tokens:
            if token.type == Token.ARGUMENT:
                usage_info_arg_tokens.append(token)
                usage_info_argument_index += 1
                del after_last_arg[:]

            elif token.type in (Token.SEPARATOR, Token.EOL, Token.EOS):
                after_last_arg.append(token)
            else:
                # Keyword name token
                del after_last_arg[:]

            if token.lineno - 1 == lineno:
                if (token.end_col_offset - 1) >= col:
                    break

        if token.type == Token.ARGUMENT:
            usage_info_argument_index -= 1

        elif after_last_arg:
            # Check if we are in prev/next based on the number of spaces found
            # up to the current cursor position.
            # i.e.: in `Call  arg ` we still need to have an usage_info_argument_index == 0
            # i.e.: in `Call  arg  ` we need to have an usage_info_argument_index == 1
            whitespaces_found = []
            if token.lineno - 1 == lineno:
                if (token.end_col_offset - 1) <= col:
                    whitespaces_found.append(token.value)
                else:
                    whitespaces_found.append(
                        token.value[: -(token.end_col_offset - col)]
                    )
            s = "".join(whitespaces_found)
            if len(s) <= 1:
                usage_info_argument_index -= 1

        if usage_info_argument_index == -1:
            return -1

        active_parameter: int = -1

        try:
            arg_token = usage_info_arg_tokens[usage_info_argument_index]
        except IndexError:
            pass
        else:
            if arg_token is not None:
                token_id_to_match: Dict[int, _Match] = {}
                for (
                    _error
                ) in self._collect_keyword_usage_errors_and_build_definition_map(
                    usage_info, token_id_to_match, collect_errors=False
                ):
                    pass

                matched = token_id_to_match.get(id(arg_token))
                if matched is not None:
                    active_parameter = matched.get_active_parameter_in_definition()

        # Something didn't work out...
        if active_parameter == -1:
            return self._compute_active_parameter_fallback(
                usage_info_argument_index, usage_info_arg_tokens
            )
        return active_parameter

    def collect_keyword_usage_errors(
        self,
        usage_info: UsageInfoForKeywordArgumentAnalysis,
    ) -> Iterator[Error]:
        yield from self._collect_keyword_usage_errors_and_build_definition_map(
            usage_info
        )
