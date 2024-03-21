import os
from functools import lru_cache
from typing import Optional, Tuple, List, Iterator, Union
from robotframework_ls.impl.protocols import (
    IRobotVariableMatch,
    IRobotToken,
    ICompletionContext,
    AbstractVariablesCollector,
    IVariableFound,
)
from robocorp_ls_core.protocols import Sentinel
from robocorp_ls_core.robotframework_log import get_logger
import threading
import re

log = get_logger(__name__)


def is_number_var(normalized_variable_name):
    # see: robot.variables.finders.NumberFinder
    try:
        bases = {"0b": 2, "0o": 8, "0x": 16}
        if normalized_variable_name.startswith(tuple(bases)):
            int(normalized_variable_name[2:], bases[normalized_variable_name[:2]])
            return True
        int(normalized_variable_name)
        return True
    except:
        pass  # Let's try float...

    try:
        float(normalized_variable_name)
        return True
    except:
        pass

    return False


def is_python_eval_var(normalized_variable_name):
    return (
        len(normalized_variable_name) >= 2
        and normalized_variable_name[0] == "{"
        and normalized_variable_name[-1] == "}"
    )


_separator_chars = [re.escape(c) for c in """./\()"'-:,.;<>~!@#$%^&*|+=[]{}`~?"""]

_match_extended = re.compile(
    r"""
    (.+?)          # base name (group 1)
    ([%s].+)    # extended part (group 2)
"""
    % "|".join(_separator_chars),
    re.UNICODE | re.VERBOSE,
).match


# _match_extended = re.compile(
#     r"""
#     (.+?)          # base name (group 1)
#     ([^\s\w].+)    # extended part (group 2)
# """,
#     re.UNICODE | re.VERBOSE,
# ).match
#
# The above is the default on RF, but it doesn't work very well for emoji.
# i.e.:
#
# print(_match_extended("aa.bb").groups())
# Makes the correct thing and splits aa, .bb
#
# print(_match_extended("aa🦘bb").groups())
# Makes the INCORRECT thing and splits aa, 🦘bb
# -- The new version does the correct thing and doesn't split the emoji.


def extract_var_name_from_extended_base_name(normalized_variable_name):
    m = _match_extended(normalized_variable_name)
    if m is None:
        return normalized_variable_name

    base_name, _extended = m.groups()
    return base_name


def extract_variable_base(text: str) -> str:
    """
    Converts something as: "${S_ome.VAR}[foo]" to "S_ome.VAR".
    """
    variable_match = robot_search_variable(text)
    if variable_match is not None:
        base = variable_match.base
        if base is not None:
            return base

    if len(text) >= 3:
        if (
            text.endswith("}")
            and text[1] == "{"
            and text.startswith(("$", "@", "&", "%"))
        ):
            return text[2:-1]
    return text


@lru_cache(maxsize=500)
def normalize_variable_name(text: str) -> str:
    """
    Converts something as: "${S_ome.VAR}[foo]" to "some.var".
    """
    base = extract_variable_base(text)

    return base.lower().replace("_", "").replace(" ", "")


@lru_cache(maxsize=200)
def robot_search_variable(text: str) -> Optional[IRobotVariableMatch]:
    """
    Provides the IRobotVariableMatch from a text such as "${S_ome.VAR}[foo]".
    """
    from robot.variables.search import search_variable  # type:ignore

    try:
        variable_match = search_variable(text, identifiers="$@&%", ignore_errors=True)
        return variable_match
    except:
        pass

    return None


def has_variable(text: str) -> bool:
    robot_match = robot_search_variable(text)
    if robot_match is None:
        return False
    return bool(robot_match.base)


def iter_robot_variable_matches(
    string: str,
) -> Iterator[Tuple[IRobotVariableMatch, int]]:
    """
    Provides the IRobotVariableMatch and the relative index for the match in the string.
    """
    # Based on robot.variables.search.VariableIterator
    remaining = string
    relative_index = 0
    while True:
        robot_match = robot_search_variable(remaining)
        if not robot_match:
            break
        yield robot_match, relative_index
        remaining = robot_match.after
        relative_index += len(robot_match.before) + len(robot_match.match)


def find_split_index(string: str) -> int:
    # Based on: robot.utils.escaping.split_from_equals
    # Based on: robot.utils.escaping._find_split_index

    eq_i = string.find("=")
    if eq_i == -1:
        return -1

    return _find_split_index(string, eq_i)


@lru_cache(maxsize=200)
def _find_split_index(string: str, eq_i: int) -> int:
    try:
        variables = tuple(iter_robot_variable_matches(string))
        if not variables and "\\" not in string:
            return eq_i

        relative_index = 0
        robot_match_len = 0
        for robot_match, relative_index in variables:
            before = robot_match.before
            string = robot_match.after
            try:
                return _find_split_index_from_part(before) + relative_index
            except ValueError:
                pass
            robot_match_len = robot_match.end - robot_match.start + len(before)

        return _find_split_index_from_part(string) + relative_index + robot_match_len
    except ValueError:
        return -1


def _find_split_index_from_part(string):
    index = 0
    while "=" in string[index:]:
        index += string[index:].index("=")
        if _not_escaping(string[:index]):
            return index
        index += 1
    raise ValueError()


def _not_escaping(name):
    backslashes = len(name) - len(name.rstrip("\\"))
    return backslashes % 2 == 0


class _VariablesCollector(AbstractVariablesCollector):
    def __init__(self):
        self.var_name_to_var_found = {}

    def accepts(self, variable_name: str) -> bool:
        return True

    def on_variable(self, variable_found: IVariableFound):
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        self.var_name_to_var_found[
            normalize_robot_name(variable_found.variable_name)
        ] = variable_found


class ResolveVariablesContext:
    _thread_local = threading.local()

    def __init__(self, completion_context: ICompletionContext):
        self.config = completion_context.config
        self.completion_context = completion_context

    @property
    def doc_path(self) -> str:
        return self.completion_context.doc.path

    def _resolve_environment_variable(self, var_name, value_if_not_found, log_info):
        ret = os.environ.get(var_name, Sentinel.SENTINEL)
        if ret is Sentinel.SENTINEL:
            log.info(*log_info)
            return value_if_not_found
        return ret

    def _convert_robot_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized = normalize_robot_name(var_name)

        if normalized == "curdir":
            return os.path.dirname(self.doc_path)

        completion_context = self.completion_context

        # Settings and argument files have higher priority (arguments override things
        # in the document).
        found = completion_context.get_settings_normalized_var_name_to_var_found().get(
            normalized
        )
        if found is not None:
            return found.variable_value

        found = completion_context.get_arguments_files_normalized_var_name_to_var_found().get(
            normalized
        )
        if found is not None:
            return found.variable_value

        found = completion_context.get_variables_files_normalized_var_name_to_var_found().get(
            normalized
        )
        if found is not None:
            return found.variable_value

        found = completion_context.get_doc_normalized_var_name_to_var_found().get(
            normalized
        )

        if found is not None:
            return found.variable_value

        found = completion_context.get_builtins_normalized_var_name_to_var_found(
            True
        ).get(normalized)
        if found is not None:
            return found.variable_value

        # At this point we have to do a search in the imports to check whether
        # maybe the variable is defined in a dependency. Note that we can get
        # into a recursion here as we may need to resolve other variables
        # in order to get here.
        # It goes something like:
        # Resolve variable -> some variable
        # collect dependencies (which may need to resolve variables again).
        # In this case we have a thread-local variable to know whether this is the
        # case and if it is bail out.
        try:
            resolve_info = self._thread_local.resolve_info
        except:
            resolve_info = self._thread_local.resolve_info = set()

        if var_name in resolve_info:
            log.info("Unable to find robot variable: %s", var_name)
            return value_if_not_found

        else:
            try:
                resolve_info.add(var_name)

                from robotframework_ls.impl.variable_completions import (
                    collect_global_variables_from_document_dependencies,
                )

                collector = _VariablesCollector()

                collect_global_variables_from_document_dependencies(
                    completion_context, collector
                )

                found = collector.var_name_to_var_found.get(normalized)
                if found is not None:
                    return found.variable_value

                log.info("Unable to find robot variable: %s", var_name)
                return value_if_not_found
            finally:
                resolve_info.discard(var_name)

    def _convert_environment_variable(
        self, var_name, value_if_not_found
    ) -> Optional[str]:
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV

        i = var_name.find("=")
        if i > 0:
            value_if_not_found = var_name[i + 1 :]
            var_name = var_name[:i]

        if self.config is None:
            value = self._resolve_environment_variable(
                var_name,
                value_if_not_found,
                (
                    "Config not available while trying to convert environment variable: %s",
                    var_name,
                ),
            )
        else:
            robot_env_vars = self.config.get_setting(OPTION_ROBOT_PYTHON_ENV, dict, {})
            value = robot_env_vars.get(var_name, Sentinel.SENTINEL)
            if value is Sentinel.SENTINEL:
                value = self._resolve_environment_variable(
                    var_name,
                    value_if_not_found,
                    ("Unable to find environment variable: %s", var_name),
                )

        if value is None:
            return None
        return str(value)

    def token_value_resolving_variables(self, token: IRobotToken) -> str:
        return self.token_value_and_unresolved_resolving_variables(token)[0]

    def token_value_and_unresolved_resolving_variables(
        self, token: Union[IRobotToken, str], count=0
    ) -> Tuple[str, Tuple[Tuple[IRobotToken, str], ...]]:
        """
        :return: The new value of the token (with resolved variables) and if
        some variable was unresolved, a tuple of tuples with the token of the
        unresolved variable as well as the related error message.

        i.e.:
            (
                'resolved/var',
                (
                    (unresolved_token, error_msg), (unresolved_token, error_msg)
                )
            )
        """
        from robotframework_ls.impl import ast_utils

        robot_token: IRobotToken
        if isinstance(token, str):
            robot_token = ast_utils.create_token(token)
        else:
            robot_token = token

        try:
            tokenized_vars = ast_utils.tokenize_variables(robot_token)
        except:
            return robot_token.value, ()  # Unable to tokenize

        unresolved: List[Tuple[IRobotToken, str]] = []

        parts: List[str] = []
        tok: IRobotToken
        value: str
        for tok in tokenized_vars:
            if tok.type == tok.NAME:
                parts.append(str(tok))

            elif tok.type == tok.VARIABLE:
                if count > 6:
                    unresolved.append(
                        (
                            tok,
                            f"\nRecursion detected when resolving variable: {tok.value}.",
                        )
                    )
                    return str(tok), tuple(unresolved)
                value = str(tok)

                resolved, new_value = self._resolve_tok_var(value)
                if new_value is None:
                    new_value = value
                if not resolved:
                    unresolved.append(
                        (
                            tok,
                            f"\nUnable to statically resolve variable: {tok.value}.\nPlease set the `{tok.value[2:-1]}` value in `robot.variables`.",
                        )
                    )
                else:
                    # Ok, it was resolved, but we need to check if we need
                    # to resolve new values from that value (and do it
                    # recursively if needed).
                    for _ in range(6):
                        if "{" in new_value:
                            (
                                v2,
                                unresolved_tokens,
                            ) = self.token_value_and_unresolved_resolving_variables(
                                new_value, count + 1
                            )
                            if unresolved_tokens:
                                if len(unresolved_tokens) == 1:
                                    t = next(iter(unresolved_tokens))[0]
                                    unresolved.append(
                                        (
                                            tok,
                                            f"\nUnable to statically resolve variable: {tok.value} because dependent variable: {t.value} was not resolved.",
                                        )
                                    )
                                else:
                                    lst = []
                                    for t, _error_msg in unresolved_tokens:
                                        lst.append(t.value)

                                    unresolved.append(
                                        (
                                            tok,
                                            f"\nUnable to statically resolve variable: {tok.value} because dependent variables: {', '.join(lst)} were not resolved.",
                                        )
                                    )
                                break

                            if v2 == new_value:
                                break
                            new_value = v2
                parts.append(new_value)

        joined_parts = "".join(parts)
        return joined_parts, tuple(unresolved)

    def _resolve_tok_var(self, value: str) -> Tuple[bool, str]:
        """
        :return: whether the variable was resolved and its value (same as input if unresolved).
        """
        convert_with = None
        if value.startswith("${") and value.endswith("}"):
            convert_with = self._convert_robot_variable

        elif value.startswith("%{") and value.endswith("}"):
            convert_with = self._convert_environment_variable

        if convert_with is None:
            log.info("Cannot resolve variable: %s", value)
            return False, value  # Leave unresolved.
        else:
            inner_value = value[2:-1]
            converted = convert_with(inner_value, None)
            if converted is None:
                log.info("Cannot resolve variable: %s", value)
                return False, value
            else:
                return True, converted
