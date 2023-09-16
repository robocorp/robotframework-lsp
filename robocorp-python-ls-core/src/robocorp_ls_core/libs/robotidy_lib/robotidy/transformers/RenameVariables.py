import re
from typing import List, Pattern, Tuple

from robot.api.parsing import Arguments, Token
from robot.errors import VariableError
from robot.variables import VariableIterator
from robot.variables.search import search_variable

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.skip import Skip
from robotidy.transformers import Transformer
from robotidy.utils import after_last_dot, normalize_name

SET_GLOBAL_VARIABLES = {"settestvariable", "settaskvariable", "setsuitevariable", "setglobalvariable"}


def is_set_global_variable(keyword: str) -> bool:
    """Checks if keyword call is Set Test/Suite/Global keyword."""
    normalized_name = normalize_name(after_last_dot(keyword))
    return normalized_name in SET_GLOBAL_VARIABLES


def is_nested_variable(variable: str) -> bool:
    """Checks if variable name is nested.

    name -> not nested
    ${name} -> not nested
    ${name_${VAR}} -> nested
    """
    match = search_variable(variable, ignore_errors=True)
    if not match.base:
        return False
    match = search_variable(match.base, ignore_errors=True)
    return match.base


def resolve_var_name(name: str) -> str:
    """Resolve name of the variable from \\${name} or $name syntax."""
    if name.startswith("\\"):
        name = name[1:]
    if len(name) < 2 or name[0] not in "$@&":
        return name
    if name[1] != "{":
        name = f"{name[0]}{{{name[1:]}}}"  # Add {} brackets around name
    return name


class VariablesScope:
    def __init__(self):
        self._local = set()
        self._global = set()

    def add_global(self, variable: str):
        match = search_variable(variable, ignore_errors=True)
        if not match.base:
            return
        self._global.add(normalize_name(match.base))

    def add_local(self, variable: str, split_pattern: bool = False):
        """Add variable name to local cache.

        If the variable is embedded argument, it can contain pattern we need to ignore (${var:[^pattern]})
        """
        match = search_variable(variable, ignore_errors=True)
        if not match.base:
            return
        name = match.base
        if split_pattern:
            name = name.split(":", maxsplit=1)[0]
        self._local.add(normalize_name(name))

    def change_scope_from_local_to_global(self, variable: str):
        """
        Changes the variable scope from local to global by removing it from local cache and adding to global one.
        """
        match = search_variable(variable, ignore_errors=True)
        if not match.base:
            return
        name = match.base
        self._local.discard(normalize_name(name))
        self._global.add(normalize_name(match.base))

    def is_local(self, variable: str):
        return normalize_name(variable) in self._local

    def is_global(self, variable: str):
        return normalize_name(variable) in self._global


class RenameVariables(Transformer):
    """
    Rename and normalize variable names.

    Variable names in Settings, Variables, Test Cases and Keywords section are renamed. Variables in arguments are
    also affected.

    Following conventions are applied:

    - variable case depends on the variable scope (lowercase for local variables and uppercase for non-local variables)
    - leading and trailing whitespace is stripped
    - more than 2 consecutive whitespace in name is replaced by 1
    - whitespace is replaced by _
    - camelCase is converted to snake_case

    Conventions can be configured or switched off using parameters - read more in the documentation.

    Following code:

    ```robotframework
    *** Settings ***
    Suite Setup    ${keyword}

    *** Variables ***
    ${global}    String with {other global}

    *** Test Cases ***
    Test
        ${local}    Set Variable    variable
        Log    ${local}
        Log    ${global}
        Log    ${local['item']}

    *** Keywords ***
    Keyword
        [Arguments]    ${ARG}
        Log    ${arg}

    Keyword With ${EMBEDDED}
        Log    ${emb   eded}

    ```

    will be transformed to:

    ```robotframework
    *** Settings ***
    Suite Setup    ${KEYWORD}

    *** Variables ***
    ${GLOBAL}    String with {OTHER_GLOBAL}

    *** Test Cases ***
    Test
        ${local}    Set Variable    variable
        Log    ${local}
        Log    ${GLOBAL}
        Log    ${local['item']}

    *** Keywords ***
    Keyword
        [Arguments]    ${arg}
        Log    ${arg}

    Keyword With ${embedded}
        Log    ${emb_eded}

    ```
    """

    ENABLED = False
    HANDLES_SKIP = frozenset({"skip_sections"})
    MORE_THAN_2_SPACES: Pattern = re.compile(r"\s{2,}")
    CAMEL_CASE: Pattern = re.compile(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")
    EXTENDED_SYNTAX: Pattern = re.compile(r"(.+?)([^\s\w].+)", re.UNICODE)
    DEFAULT_IGNORE_CASE = {"\\n"}

    def __init__(
        self,
        settings_section_case: str = "upper",
        variables_section_case: str = "upper",
        unknown_variables_case: str = "upper",
        variable_separator: str = "underscore",
        convert_camel_case: bool = True,
        ignore_case: str = None,
        skip: Skip = None,
    ):
        super().__init__(skip)
        self.validate_case("settings_section_case", settings_section_case, ["upper", "lower", "ignore"])
        self.validate_case("variables_section_case", variables_section_case, ["upper", "lower", "ignore"])
        self.validate_case("unknown_variables_case", unknown_variables_case, ["upper", "lower", "ignore"])
        self.validate_variable_separator(variable_separator)
        self.settings_section_case = settings_section_case
        self.variables_section_case = variables_section_case
        self.unknown_variables_case = unknown_variables_case
        # we always convert to space, so we only need to check if we need to convert back to _
        self.replace_variable_separator = variable_separator == "underscore"
        self.convert_camel_case = convert_camel_case
        self.ignore_case = self.get_ignored_variables_case(ignore_case)
        self.variables_scope = VariablesScope()

    def validate_case(self, param_name: str, case: str, allowed_case: List):
        if case not in allowed_case:
            case_types = ", ".join(allowed_case)
            raise InvalidParameterValueError(
                self.__class__.__name__,
                param_name,
                case,
                f"Invalid case type. Allowed case types are: {case_types}",
            )

    def validate_variable_separator(self, variable_separator: str):
        if variable_separator not in ("underscore", "space"):
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "variable_separator",
                variable_separator,
                "Allowed values are: underscore, space",
            )

    def get_ignored_variables_case(self, ignore_vars):
        if ignore_vars is None:
            return self.DEFAULT_IGNORE_CASE
        ignored_vars = set(ignore_vars.split(","))
        return ignored_vars.union(self.DEFAULT_IGNORE_CASE)

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_LibraryImport(self, node):  # noqa
        for data_token in node.data_tokens[1:]:
            data_token.value = self.rename_value(
                data_token.value, variable_case=self.settings_section_case, is_var=False
            )
        return self.generic_visit(node)

    visit_DefaultTags = (
        visit_TestTags
    ) = (
        visit_ForceTags
    ) = (
        visit_Metadata
    ) = (
        visit_SuiteSetup
    ) = (
        visit_SuiteTeardown
    ) = (
        visit_TestSetup
    ) = (
        visit_TestTeardown
    ) = visit_TestTemplate = visit_TestTimeout = visit_VariablesImport = visit_ResourceImport = visit_LibraryImport

    @skip_if_disabled
    def visit_Setup(self, node):  # noqa
        for data_token in node.data_tokens[1:]:
            data_token.value = self.rename_value(data_token.value, variable_case="auto", is_var=False)
        return self.generic_visit(node)

    visit_Teardown = visit_Timeout = visit_Template = visit_Return = visit_ReturnStatement = visit_Setup

    @skip_if_disabled
    def visit_Variable(self, node):  # noqa
        if node.errors:
            return node
        for data_token in node.data_tokens:
            if data_token.type == Token.VARIABLE:
                data_token.value = self.rename_value(
                    data_token.value, variable_case=self.variables_section_case, is_var=True
                )
            elif data_token.type == Token.ARGUMENT:
                data_token.value = self.rename_value(
                    data_token.value, variable_case=self.variables_section_case, is_var=False
                )
        return node

    @skip_if_disabled
    def visit_TestCase(self, node):  # noqa
        self.variables_scope = VariablesScope()
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_TemplateArguments(self, node):  # noqa
        for arg_template in node.get_tokens(Token.ARGUMENT):
            arg_template.value = self.rename_value(arg_template.value, variable_case="auto", is_var=False)
        return self.generic_visit(node)  # noqa

    @skip_if_disabled
    def visit_TestCaseName(self, node):  # noqa
        for token in node.data_tokens:
            name = ""
            for name_token in token.tokenize_variables():
                if name_token.type == Token.VARIABLE:
                    name_token.value = self.rename_value(name_token.value, variable_case="upper", is_var=True)
                name += name_token.value
            token.value = name
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_KeywordName(self, node):  # noqa
        for token in node.data_tokens:
            name = ""
            for name_token in token.tokenize_variables():
                if name_token.type == Token.VARIABLE:
                    self.variables_scope.add_local(name_token.value, split_pattern=True)
                    name_token.value = self.rename_value(name_token.value, variable_case="lower", is_var=True)
                name += name_token.value
            token.value = name
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_Keyword(self, node):  # noqa
        self.variables_scope = VariablesScope()
        # we need to find arguments before visiting body
        for statement in node.body:
            if isinstance(statement, Arguments):
                for arg in statement.get_tokens(Token.ARGUMENT):
                    if "=" in arg.value:
                        variable, default = arg.value.split("=", maxsplit=1)
                        self.variables_scope.add_local(variable)
                        # is_var=False because it can contain space ie ${var} =
                        variable = self.rename_value(variable, variable_case="lower", is_var=False)
                        # default value can contain other argument, so we need to auto-detect case
                        default = self.rename_value(default, variable_case="auto", is_var=False)
                        arg.value = f"{variable}={default}"
                    else:
                        self.variables_scope.add_local(arg.value)
                        arg.value = self.rename_value(arg.value, variable_case="lower", is_var=True)
        return self.generic_visit(node)

    def visit_KeywordCall(self, node):  # noqa
        if not self.disablers.is_node_disabled(node):
            for token in node.data_tokens:
                if token.type == Token.ASSIGN:
                    token.value = self.rename_value(token.value, variable_case="lower", is_var=False)
                elif token.type in (Token.ARGUMENT, Token.KEYWORD):
                    token.value = self.rename_value(token.value, variable_case="auto", is_var=False)
        # we need to add assign to local scope after iterating keyword call because of
        # ${overwritten_scope}  Set Variable  ${OVERWRITTEN_SCOPE}  case
        for assign_token in node.get_tokens(Token.ASSIGN):
            self.variables_scope.add_local(assign_token.value)
        self.uppercase_global_name_in_set_variable(node)
        return node

    def uppercase_global_name_in_set_variable(self, node):
        if not is_set_global_variable(node.keyword):
            return
        args = node.get_tokens(Token.ARGUMENT)
        if len(args) < 1:
            return
        if not is_nested_variable(args[0].value):
            args[0].value = args[0].value.upper()
            resolved_var = resolve_var_name(args[0].value)  # convert $name
            self.variables_scope.change_scope_from_local_to_global(resolved_var)

    @skip_if_disabled
    def visit_For(self, node):  # noqa
        for token in node.header:
            if token.type == Token.VARIABLE:
                self.variables_scope.add_local(token.value)
                token.value = self.rename_value(token.value, variable_case="lower", is_var=True)
            elif token.type == Token.ARGUMENT:
                token.value = self.rename_value(token.value, variable_case="auto", is_var=False)
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_Try(self, node):  # noqa
        if node.variable is not None:
            error_var = node.header.get_token(Token.VARIABLE)
            if error_var is not None:
                self.variables_scope.add_local(error_var.value)
                error_var.value = self.rename_value(error_var.value, variable_case="lower", is_var=True)
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_If(self, node):  # noqa
        if node.errors:
            return node
        for token in node.header.data_tokens:
            if token.type == Token.ASSIGN:
                self.variables_scope.add_local(token.value)
                token.value = self.rename_value(token.value, variable_case="lower", is_var=False)
            elif token.type == Token.ARGUMENT:
                token.value = self.rename_value(token.value, variable_case="auto", is_var=False)
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_While(self, node):  # noqa
        for arg in node.header.get_tokens(Token.ARGUMENT):
            arg.value = self.rename_value(arg.value, variable_case="auto", is_var=False)
        return self.generic_visit(node)

    def rename_value(self, value: str, variable_case: str, is_var: bool = False):
        try:
            variables = list(VariableIterator(value))
        except VariableError:  # for example ${variable which wasn't closed properly
            variables = []
        if not variables:
            if is_var:
                return self.rename(value, case=variable_case, strip_fn="strip")
            return value
        name = ""
        remaining = ""
        for before, variable, remaining in variables:
            if before:
                if is_var:
                    name += self.rename(before, case=variable_case, strip_fn="lstrip")
                else:
                    name += before
            # handle ${variable}[item][${syntax}]
            match = search_variable(variable, ignore_errors=True)
            # inline eval will start and end with {}
            if not (match.base.startswith("{") and match.base.endswith("}")):
                base = self.rename_value(match.base, variable_case=variable_case, is_var=True)
                base = f"{match.name[:2]}{base}}}"
            else:
                base = match.name
            for item in match.items:
                renamed_item = self.rename_value(item, variable_case=variable_case, is_var=False)
                base += f"[{renamed_item}]"
            name += base
        if remaining:
            if is_var:
                name += self.rename(remaining, case=variable_case, strip_fn="rstrip")
            else:
                name += remaining
        return name

    def set_name_case(self, name: str, case: str):
        if name in self.ignore_case:
            return name
        if case == "upper":
            return name.upper()
        if case == "lower":
            return name.lower()
        if case == "auto":
            return self.set_case_for_local_and_global(name)
        return name

    def set_case_for_local_and_global(self, name):
        if self.variables_scope.is_local(name):
            return name.lower()
        if self.variables_scope.is_global(name):
            return name.upper()
        extended_syntax = self.EXTENDED_SYNTAX.match(name)
        if extended_syntax is None:
            return self.set_name_case(name, self.unknown_variables_case)
        base_name, extended = extended_syntax.groups()
        return self.set_case_for_local_and_global(base_name) + extended

    def rename(self, variable_value: str, case: str, strip_fn: str = "strip"):
        if not variable_value:
            return variable_value
        # split on variable attribute access like ${var['item']}, ${var.item}, ${var(method)}..
        variable_name, item_access = split_string_on_delimiter(variable_value)
        if self.convert_camel_case:
            variable_name = self.CAMEL_CASE.sub(r" \1", variable_name)
        variable_name = variable_name.replace("_", " ")
        variable_name = self.MORE_THAN_2_SPACES.sub(" ", variable_name)
        if variable_name == " ":  # ${ } or ${_}
            return "_" + item_access
        # to handle cases like ${var_${variable}_} we need to only strip whitespace at start/end depending on the type
        if strip_fn == "strip":
            variable_name = variable_name.strip()
        elif strip_fn == "lstrip":
            variable_name = variable_name.lstrip()
        elif strip_fn == "rstrip":
            variable_name = variable_name.rstrip()
        if self.replace_variable_separator:
            variable_name = variable_name.replace(" ", "_")
        variable_name = self.set_name_case(variable_name, case)
        return variable_name + item_access


def split_string_on_delimiter(string: str) -> Tuple[str, str]:
    """
    Split string on first occurrence of the delimiters.

    Return string before and after split, retaining delimiter.

    Following strings returns:

        item -> 'item', ''
        item.value -> 'item', '.value'
        item['value'] -> 'item', '['value']

    """
    delimiters = {".", "[", "(", ":"}
    for index, char in enumerate(string):
        if char in delimiters:
            return string[:index], string[index:]
    return string, ""
