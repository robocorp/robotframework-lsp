import os
from functools import lru_cache
from typing import Optional, Union, Tuple, List, Iterator
from robotframework_ls.impl.protocols import IRobotVariableMatch, IRobotToken
from robocorp_ls_core.protocols import Sentinel, IConfig
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


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
        if text.endswith("}") and text[1] == "{":
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

        for robot_match, relative_index in variables:
            before, string = (
                robot_match.before,
                robot_match.after,
            )
            try:
                return _find_split_index_from_part(before) + relative_index
            except ValueError:
                pass
        return _find_split_index_from_part(string) + relative_index
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


class ResolveVariablesContext:
    def __init__(self, config: Optional[IConfig], doc_path: str):
        self.config = config
        self.doc_path = doc_path

    def _resolve_builtin(self, var_name, value_if_not_found, log_info):
        from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES_RESOLVED

        ret = BUILTIN_VARIABLES_RESOLVED.get(var_name, Sentinel.SENTINEL)
        if ret is Sentinel.SENTINEL:
            if var_name == "CURDIR":
                return os.path.dirname(self.doc_path)
            log.info(*log_info)
            return value_if_not_found
        return ret

    def _resolve_environment_variable(self, var_name, value_if_not_found, log_info):
        ret = os.environ.get(var_name, Sentinel.SENTINEL)
        if ret is Sentinel.SENTINEL:
            log.info(*log_info)
            return value_if_not_found
        return ret

    def _convert_robot_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

        if self.config is None:
            value = self._resolve_builtin(
                var_name,
                value_if_not_found,
                (
                    "Config not available while trying to convert robot variable: %s",
                    var_name,
                ),
            )
        else:
            robot_variables = self.config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
            value = robot_variables.get(var_name, Sentinel.SENTINEL)
            if value is Sentinel.SENTINEL:
                value = self._resolve_builtin(
                    var_name,
                    value_if_not_found,
                    ("Unable to find robot variable: %s", var_name),
                )

        value = str(value)
        return value

    def _convert_environment_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV

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

        value = str(value)
        return value

    def token_value_resolving_variables(self, token: Union[str, IRobotToken]) -> str:
        from robotframework_ls.impl import ast_utils

        robot_token: IRobotToken
        if isinstance(token, str):
            robot_token = ast_utils.create_token(token)
        else:
            robot_token = token

        try:
            tokenized_vars = ast_utils.tokenize_variables(robot_token)
        except:
            return robot_token.value  # Unable to tokenize

        parts = []
        for v in tokenized_vars:
            if v.type == v.NAME:
                parts.append(str(v))

            elif v.type == v.VARIABLE:
                # Resolve variable from config
                initial_v = v = str(v)
                if v.startswith("${") and v.endswith("}"):
                    v = v[2:-1]
                    parts.append(self._convert_robot_variable(v, initial_v))
                elif v.startswith("%{") and v.endswith("}"):
                    v = v[2:-1]
                    parts.append(self._convert_environment_variable(v, initial_v))
                else:
                    log.info("Cannot resolve variable: %s", v)
                    parts.append(v)  # Leave unresolved.

        joined_parts = "".join(parts)
        return joined_parts

    def token_value_and_unresolved_resolving_variables(
        self, token: IRobotToken
    ) -> Tuple[str, Tuple[IRobotToken, ...]]:
        unresolved: List[IRobotToken] = []

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

        parts = []
        for tok in tokenized_vars:
            if tok.type == tok.NAME:
                parts.append(str(tok))

            elif tok.type == tok.VARIABLE:
                # Resolve variable from config
                initial_v = v = str(tok)
                if v.startswith("${") and v.endswith("}"):
                    v = v[2:-1]
                    converted = self._convert_robot_variable(v, initial_v)
                    parts.append(converted)
                    if converted == initial_v:
                        # Unable to resolve
                        unresolved.append(tok)

                elif v.startswith("%{") and v.endswith("}"):
                    v = v[2:-1]
                    converted = self._convert_environment_variable(v, initial_v)
                    parts.append(converted)
                    if converted == initial_v:
                        # Unable to resolve
                        unresolved.append(tok)

                else:
                    log.info("Cannot resolve variable: %s", v)
                    parts.append(v)  # Leave unresolved.

        joined_parts = "".join(parts)
        return joined_parts, tuple(unresolved)
