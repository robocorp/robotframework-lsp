"""
Naming checkers
"""
import re
from collections import defaultdict
from pathlib import Path

from robot.api import Token
from robot.parsing.model.blocks import Keyword
from robot.parsing.model.statements import Arguments, KeywordCall

from robocop.checkers import VisitorChecker
from robocop.rules import Rule, RuleParam, RuleSeverity
from robocop.utils import (
    ROBOT_VERSION,
    find_robot_vars,
    keyword_col,
    normalize_robot_name,
    normalize_robot_var_name,
    pattern_type,
    remove_robot_vars,
    token_col,
)
from robocop.utils.run_keywords import iterate_keyword_names

rules = {
    "0301": Rule(
        RuleParam(
            name="pattern",
            default=re.compile(r"[\.\?]"),
            converter=pattern_type,
            desc="pattern defining characters (not) allowed in a name",
        ),
        rule_id="0301",
        name="not-allowed-char-in-name",
        msg="Not allowed character '{{ character }}' found in {{ block_name }} name",
        severity=RuleSeverity.WARNING,
        docs="""
        Reports not allowed pattern found in Test Case or Keyword names. By default it's dot (`.`). You can
        configure what patterns are reported by calling::

             robocop --configure not-allowed-char-in-name:pattern:regex_pattern

        `regex_pattern` should define regex pattern not allowed in names. For example `[@\[]` pattern
        reports any occurrence of `@[` characters.
        """,
    ),
    "0302": Rule(
        RuleParam(
            name="convention",
            default="each_word_capitalized",
            converter=str,
            desc="possible values: 'each_word_capitalized' (default) or 'first_word_capitalized'",
        ),
        RuleParam(
            name="pattern",
            default=re.compile(r""),
            converter=pattern_type,
            desc="pattern for accepted words in keyword",
        ),
        rule_id="0302",
        name="wrong-case-in-keyword-name",
        msg="Keyword name '{{ keyword_name }}' does not follow case convention",
        severity=RuleSeverity.WARNING,
    ),
    "0303": Rule(
        rule_id="0303",
        name="keyword-name-is-reserved-word",
        msg="'{{ keyword_name }}' is a reserved keyword{{ error_msg }}",
        severity=RuleSeverity.ERROR,
        docs="""
        Do not use reserved names for keyword names. Following names are reserved:

          - IF
          - ELSE IF
          - ELSE
          - FOR
          - END
          - WHILE
          - CONTINUE
          - RETURN
          - TRY
          - EXCEPT

        """,
    ),
    "0305": Rule(
        rule_id="0305",
        name="underscore-in-keyword-name",
        msg="Underscores in keyword name '{{ keyword_name }}' can be replaced with spaces",
        severity=RuleSeverity.WARNING,
        docs="""
        Example::

            # bad
            keyword_with_underscores

            # good
            Keyword Without Underscores

        """,
    ),
    "0306": Rule(
        rule_id="0306",
        name="setting-name-not-in-title-case",
        msg="Setting name '{{ setting_name }}' should use title or upper case",
        severity=RuleSeverity.WARNING,
        docs="""
        Good::

             *** Settings ***
             Resource    file.resource

             *** Test Cases ***
             Test
                 [DOCUMENTATION]  Some documentation
                 Step

        Bad::

             *** Settings ***
             resource    file.resource

             *** Test Cases ***
             Test
                 [documentation]  Some documentation
                 Step

        """,
    ),
    "0307": Rule(
        rule_id="0307",
        name="section-name-invalid",
        msg="Section name should be in format '{{ section_title_case }}' or '{{ section_upper_case }}'",
        severity=RuleSeverity.WARNING,
        docs="""
        Good::

            *** SETTINGS ***
            *** Keywords ***

        Bad::

            *** keywords ***

        """,
    ),
    "0308": Rule(
        rule_id="0308",
        name="not-capitalized-test-case-title",
        msg="Test case '{{ test_name }}' title should start with capital letter",
        severity=RuleSeverity.WARNING,
    ),
    "0309": Rule(
        rule_id="0309",
        name="section-variable-not-uppercase",
        msg="Section variable '{{ variable_name }}' name should be uppercase",
        severity=RuleSeverity.WARNING,
    ),
    "0310": Rule(
        rule_id="0310",
        name="non-local-variables-should-be-uppercase",
        msg="Test, suite and global variables should be uppercase",
        severity=RuleSeverity.WARNING,
    ),
    "0311": Rule(
        rule_id="0311",
        name="else-not-upper-case",
        msg="ELSE and ELSE IF should be upper case",
        severity=RuleSeverity.ERROR,
    ),
    "0312": Rule(
        rule_id="0312",
        name="keyword-name-is-empty",
        msg="Keyword name should not be empty",
        severity=RuleSeverity.ERROR,
    ),
    "0313": Rule(
        rule_id="0313",
        name="test-case-name-is-empty",
        msg="Test case name should not be empty",
        severity=RuleSeverity.ERROR,
    ),
    "0314": Rule(
        rule_id="0314",
        name="empty-library-alias",
        msg="Library alias should not be empty",
        severity=RuleSeverity.ERROR,
        docs="""
        Use non-empty name when using library import with alias.

        Good::

            *** Settings ***
            Library  CustomLibrary  AS  AnotherName

        Bad::

             *** Settings ***
             Library  CustomLibrary  AS

        """,
    ),
    "0315": Rule(
        rule_id="0315",
        name="duplicated-library-alias",
        msg="Library alias should not be the same as original name",
        severity=RuleSeverity.WARNING,
        docs="""
        Example of rule violation::

             *** Settings ***
             Library  CustomLibrary  AS  CustomLibrary  # same as library name
             Library  CustomLibrary  AS  Custom Library  # same as library name (spaces are ignored)

        """,
    ),
    "0316": Rule(
        rule_id="0316",
        name="possible-variable-overwriting",
        msg="Variable '{{ variable_name }}' may overwrite similar variable inside '{{ block_name }}' {{ block_type }}. "
        "Note that variables are case-insensitive, and also spaces and underscores are ignored.",
        severity=RuleSeverity.INFO,
    ),
    "0317": Rule(
        rule_id="0317",
        name="hyphen-in-variable-name",
        msg="Use underscore in variable name '{{ variable_name }}' instead of hyphens to "
        "avoid treating them like minus sign",
        severity=RuleSeverity.INFO,
        docs="""
        Robot Framework supports evaluation of Python code inside ${ } brackets. For example::

             ${var2}  Set Variable  ${${var}-${var2}}

        That's why there is possibility that hyphen in name is not recognized as part of name but as minus sign.
        Better to use underscore (if it's intended)::

        ${var2}  Set Variable  ${ ${var}_${var2}}
        """,
    ),
    "0318": Rule(
        rule_id="0318",
        name="bdd-without-keyword-call",
        msg="BDD reserved keyword '{{ keyword_name }}' not followed by any keyword{{ error_msg }}",
        severity=RuleSeverity.WARNING,
        docs="""
        When using BDD reserved keywords (such as `GIVEN`, `WHEN`, `AND`, `BUT` or `THEN`) use them together with
        name of the keyword to run.

        Good::

            Given Setup Is Complete
            When User Log In
            Then User Should See Welcome Page

        Bad::

            Given
            When User Log In
            Then User Should See Welcome Page

        Since those words are used for BDD style it's also recommended not to use them within the keyword name.
        """,
    ),
    "0319": Rule(
        rule_id="0319",
        name="deprecated-statement",
        msg="'{{ statement_name }}' is deprecated since Robot Framework version "
        "{{ version }}, use '{{ alternative }}' instead",
        severity=RuleSeverity.WARNING,
    ),
    "0320": Rule(
        RuleParam(
            name="pattern",
            default=re.compile(r"[\.\?]"),
            converter=pattern_type,
            desc="pattern defining characters (not) allowed in a name",
        ),
        rule_id="0320",
        name="not-allowed-char-in-filename",
        msg="Not allowed character '{{ character }}' found in {{ block_name }} name",
        severity=RuleSeverity.WARNING,
        docs="""
        Reports not allowed pattern found in Suite names. By default it's dot (`.`). You can
        configure what characters are reported by calling::

             robocop --configure not-allowed-char-in-filename:pattern:regex_pattern

        `regex_pattern` should define regex pattern for characters not allowed in names. For example `[@\[]` pattern
        reports any occurrence of `@[` characters.
        """,
    ),
    "0321": Rule(
        rule_id="0321",
        name="deprecated-with-name",
        msg=(
            "'WITH NAME' alias marker is deprecated since Robot Framework 5.1 version "
            "and will be removed in the future release. Use 'AS' instead"
        ),
        severity=RuleSeverity.WARNING,
        version=">=5.1",
        docs="""
        ``WITH NAME`` marker that is used when giving an alias to an imported library is going to be renamed to ``AS``.
        The motivation is to be consistent with Python that uses ``as`` for similar purpose.
        
        Code with the deprecated marker::
        
            *** Settings ***
            Library    Collections    WITH NAME    AliasedName
        
        Code with the supported marker::
        
            *** Settings ***
            Library    Collections    AS    AliasedName
        
        """,
    ),
}


class InvalidCharactersInNameChecker(VisitorChecker):
    """Checker for invalid characters in suite, test case or keyword name."""

    reports = (
        "not-allowed-char-in-filename",
        "not-allowed-char-in-name",
    )

    def visit_File(self, node):
        source = node.source if node.source else self.source
        if source:
            suite_name = Path(source).stem
            if "__init__" in suite_name:
                suite_name = Path(source).parent.name
            for iter in self.param("not-allowed-char-in-filename", "pattern").finditer(
                suite_name
            ):
                self.report(
                    "not-allowed-char-in-filename",
                    character=iter.group(),
                    block_name="suite",
                    node=node,
                    col=node.col_offset + iter.start(0) + 1,
                )
        super().visit_File(node)

    def check_if_pattern_in_node_name(self, node, name_of_node, is_keyword=False):
        """Search if regex pattern found from node name.
        Skips embedded variables from keyword name
        """
        node_name = node.name
        variables = find_robot_vars(node_name) if is_keyword else []
        start_pos = 0
        for variable in variables:
            # Loop and skip variables:
            # Search pattern from start_pos to variable starting position
            # example `Keyword With ${em.bedded} Two ${second.Argument} Argument``
            # is splitted to:
            #   1. `Keyword With `
            #   2. ` Two `
            #   3. ` Argument` - last part is searched in finditer part after this loop
            tmp_node_name = node_name[start_pos : variable[0]]
            match = self.param("not-allowed-char-in-name", "pattern").search(
                tmp_node_name
            )
            if match:
                self.report(
                    "not-allowed-char-in-name",
                    character=match.group(),
                    block_name=f"'{node_name}' {name_of_node}",
                    node=node,
                    col=node.col_offset + match.start(0) + 1,
                )
            start_pos = variable[1]

        for iter in self.param("not-allowed-char-in-name", "pattern").finditer(
            node_name, start_pos
        ):
            self.report(
                "not-allowed-char-in-name",
                character=iter.group(),
                block_name=f"'{node.name}' {name_of_node}",
                node=node,
                col=node.col_offset + iter.start(0) + 1,
            )

    def visit_TestCaseName(self, node):  # noqa
        self.check_if_pattern_in_node_name(node, "test case")

    def visit_KeywordName(self, node):  # noqa
        self.check_if_pattern_in_node_name(node, "keyword", is_keyword=True)


def reserved_error_msg(name, reserved_type):
    return (
        f". It must be in uppercase ({name.upper()}) when used as a marker with {reserved_type}. "
        f"Each marker should have minimum of 2 spaces as separator."
    )


def uppercase_error_msg(name):
    return f". It must be in uppercase ({name.upper()}) when used as a statement"


class KeywordNamingChecker(VisitorChecker):
    """Checker for keyword naming violations."""

    reports = (
        "wrong-case-in-keyword-name",
        "keyword-name-is-reserved-word",
        "underscore-in-keyword-name",
        "else-not-upper-case",
        "keyword-name-is-empty",
        "bdd-without-keyword-call",
    )
    reserved_words = {
        3: {
            "for": reserved_error_msg("for", "'FOR' loop"),
            "end": reserved_error_msg("end", "'FOR' loop"),
        },
        4: {
            "if": uppercase_error_msg("if"),
            "else if": uppercase_error_msg("else if"),
            "else": uppercase_error_msg("else"),
            "for": reserved_error_msg("for", "'FOR' loop"),
            "end": reserved_error_msg("end", "'FOR' or 'IF'"),
        },
        5: {
            "if": uppercase_error_msg("if"),
            "else if": uppercase_error_msg("else if"),
            "else": uppercase_error_msg("else"),
            "for": reserved_error_msg("for", "'FOR' loop"),
            "end": reserved_error_msg("end", "'FOR', 'IF' or 'TRY EXCEPT'"),
            "while": uppercase_error_msg("while"),
            "continue": uppercase_error_msg("continue"),
            "return": uppercase_error_msg("return"),
            "try": reserved_error_msg("try", "'TRY EXCEPT'"),
            "except": reserved_error_msg("except", "'TRY EXCEPT'"),
            "finally": reserved_error_msg("finally", "'TRY EXCEPT'"),
        },
        6: {
            "if": uppercase_error_msg("if"),
            "else if": uppercase_error_msg("else if"),
            "else": uppercase_error_msg("else"),
            "for": reserved_error_msg("for", "'FOR' loop"),
            "end": reserved_error_msg("end", "'FOR', 'IF' or 'TRY EXCEPT'"),
            "while": uppercase_error_msg("while"),
            "continue": uppercase_error_msg("continue"),
            "return": uppercase_error_msg("return"),
            "try": reserved_error_msg("try", "'TRY EXCEPT'"),
            "except": reserved_error_msg("except", "'TRY EXCEPT'"),
            "finally": reserved_error_msg("finally", "'TRY EXCEPT'"),
        },
    }
    else_statements = {"else", "else if"}
    bdd = {"given", "when", "and", "but", "then"}

    def __init__(self):
        self.letter_pattern = re.compile(r"[^\w()-]|_", re.UNICODE)
        self.inside_if_block = False
        super().__init__()

    def check_keyword_naming_with_subkeywords(self, node, name_token_type):
        for keyword in iterate_keyword_names(node, name_token_type):
            self.check_keyword_naming(keyword.value, keyword)

    def visit_Setup(self, node):  # noqa
        self.check_bdd_keywords(node.name, node)
        self.check_keyword_naming_with_subkeywords(node, Token.NAME)

    visit_TestTeardown = (
        visit_SuiteTeardown
    ) = visit_Teardown = visit_TestSetup = visit_SuiteSetup = visit_Setup

    def visit_Keyword(self, node):  # noqa
        if not node.name:
            self.report("keyword-name-is-empty", node=node)
        else:
            self.check_keyword_naming(node.name, node)
        self.generic_visit(node)

    def visit_KeywordCall(self, node):  # noqa
        if (
            self.inside_if_block
            and node.keyword
            and node.keyword.lower() in self.else_statements
        ):
            self.report("else-not-upper-case", node=node, col=keyword_col(node))
        self.check_keyword_naming_with_subkeywords(node, Token.KEYWORD)
        self.check_bdd_keywords(node.keyword, node)

    def visit_If(self, node):  # noqa
        self.inside_if_block = True
        self.generic_visit(node)
        self.inside_if_block = False

    def check_keyword_naming(self, keyword_name, node):  # noqa
        if not keyword_name or keyword_name.lstrip().startswith("#"):
            return
        if keyword_name == r"/":  # old for loop, / are interpreted as keywords
            return
        if self.check_if_keyword_is_reserved(keyword_name, node):
            return
        normalized = remove_robot_vars(keyword_name)
        normalized = self.param("wrong-case-in-keyword-name", "pattern").sub(
            "", normalized
        )
        normalized = normalized.split(".")[
            -1
        ]  # remove any imports ie ExternalLib.SubLib.Log -> Log
        normalized = normalized.replace("'", "")  # replace ' apostrophes
        if "_" in normalized:
            self.report(
                "underscore-in-keyword-name",
                keyword_name=keyword_name,
                node=node,
                col=node.col_offset + 1,
                end_col=node.end_col_offset + 1,
            )
        words = self.letter_pattern.sub(" ", normalized).split(" ")
        if (
            self.param("wrong-case-in-keyword-name", "convention")
            == "first_word_capitalized"
        ):
            words = words[:1]
        if any(word[0].islower() for word in words if word):
            self.report(
                "wrong-case-in-keyword-name",
                keyword_name=keyword_name,
                node=node,
                col=node.col_offset + 1,
                end_col=node.end_col_offset + 1,
            )

    def check_bdd_keywords(self, keyword_name, node):
        if not keyword_name or keyword_name.lower() not in self.bdd:
            return
        arg = node.get_token(Token.ARGUMENT)
        suffix = (
            f". Use one space between: '{keyword_name.title()} {arg.value}'"
            if arg
            else ""
        )
        col = token_col(node, Token.NAME, Token.KEYWORD)
        self.report(
            "bdd-without-keyword-call",
            keyword_name=keyword_name,
            error_msg=suffix,
            node=node,
            col=col,
        )

    def check_if_keyword_is_reserved(self, keyword_name, node):
        # if there is typo in syntax, it is interpreted as keyword
        reserved = self.reserved_words[ROBOT_VERSION.major]
        if keyword_name.lower() not in reserved:
            return False
        if keyword_name.lower() in self.else_statements and self.inside_if_block:
            return False  # handled by else-not-upper-case
        error_msg = reserved[keyword_name.lower()]
        self.report(
            "keyword-name-is-reserved-word",
            keyword_name=keyword_name,
            error_msg=error_msg,
            node=node,
            col=node.col_offset + 1,
            end_col=node.end_col_offset + 1,
        )
        return True


class SettingsNamingChecker(VisitorChecker):
    """Checker for settings and sections naming violations."""

    reports = (
        "setting-name-not-in-title-case",
        "section-name-invalid",
        "empty-library-alias",
        "duplicated-library-alias",
    )
    ALIAS_TOKENS = (
        [Token.WITH_NAME] if ROBOT_VERSION.major < 5 else [Token.WITH_NAME, "AS"]
    )
    # Separating alias values since RF 3 uses WITH_NAME instead of WITH NAME
    ALIAS_TOKENS_VALUES = (
        ["WITH NAME"] if ROBOT_VERSION.major < 5 else [Token.WITH_NAME, "AS"]
    )

    def __init__(self):
        self.section_name_pattern = re.compile(r"\*\*\*\s.+\s\*\*\*")
        super().__init__()

    def visit_SectionHeader(self, node):  # noqa
        name = node.data_tokens[0].value
        if not self.section_name_pattern.match(name) or not (
            name.istitle() or name.isupper()
        ):
            valid_name = f"*** {node.name.title()} ***"
            self.report(
                "section-name-invalid",
                section_title_case=valid_name,
                section_upper_case=valid_name.upper(),
                node=node,
            )

    def visit_Setup(self, node):  # noqa
        self.check_setting_name(node.data_tokens[0].value, node)

    visit_SuiteSetup = (
        visit_TestSetup
    ) = (
        visit_Teardown
    ) = (
        visit_SuiteTeardown
    ) = (
        visit_TestTeardown
    ) = (
        visit_ForceTags
    ) = (
        visit_DefaultTags
    ) = (
        visit_ResourceImport
    ) = (
        visit_VariablesImport
    ) = (
        visit_Documentation
    ) = (
        visit_Tags
    ) = visit_Timeout = visit_Template = visit_Arguments = visit_Return = visit_Setup

    def visit_LibraryImport(self, node):  # noqa
        self.check_setting_name(node.data_tokens[0].value, node)
        with_name = node.get_token(*self.ALIAS_TOKENS)
        if with_name is None:
            for arg in node.get_tokens(Token.ARGUMENT):
                if arg.value and arg.value in self.ALIAS_TOKENS_VALUES:
                    self.report("empty-library-alias", node=arg, col=arg.col_offset + 1)
        else:
            if node.alias.replace(" ", "") == node.name.replace(
                " ", ""
            ):  # New Name == NewName
                name_token = node.get_tokens(Token.NAME)[-1]
                self.report(
                    "duplicated-library-alias",
                    node=name_token,
                    col=name_token.col_offset + 1,
                )

    def check_setting_name(self, name, node):
        if not (name.istitle() or name.isupper()):
            self.report("setting-name-not-in-title-case", setting_name=name, node=node)


class TestCaseNamingChecker(VisitorChecker):
    """Checker for test case naming violations."""

    reports = (
        "not-capitalized-test-case-title",
        "test-case-name-is-empty",
    )

    def visit_TestCase(self, node):  # noqa
        if not node.name:
            self.report("test-case-name-is-empty", node=node)
        elif not node.name[0].isupper():
            self.report(
                "not-capitalized-test-case-title", test_name=node.name, node=node
            )


class VariableNamingChecker(VisitorChecker):
    """Checker for variable naming violations."""

    reports = (
        "section-variable-not-uppercase",
        "non-local-variables-should-be-uppercase",
        "hyphen-in-variable-name",
    )

    def __init__(self):
        self.set_variable_variants = {
            "settaskvariable",
            "settestvariable",
            "setsuitevariable",
            "setglobalvariable",
        }
        super().__init__()

    def visit_VariableSection(self, node):  # noqa
        for child in node.body:
            if not child.data_tokens:
                continue
            token = child.data_tokens[0]
            if (
                token.type == Token.VARIABLE
                and token.value
                and not token.value.isupper()
            ):
                self.report(
                    "section-variable-not-uppercase",
                    variable_name=token.value,
                    lineno=token.lineno,
                    col=token.col_offset + 1,
                )

    def visit_KeywordCall(self, node):  # noqa
        for token in node.get_tokens(Token.ASSIGN):
            if "-" in token.value:
                self.report(
                    "hyphen-in-variable-name",
                    variable_name=token.value,
                    lineno=token.lineno,
                    col=token.col_offset + 1,
                )

        if not node.keyword:
            return
        if (
            normalize_robot_name(node.keyword, remove_prefix="builtin.")
            in self.set_variable_variants
        ):
            if len(node.data_tokens) < 2:
                return
            token = node.data_tokens[1]
            if token.type == Token.ARGUMENT and not token.value.isupper():
                self.report(
                    "non-local-variables-should-be-uppercase",
                    node=node,
                    col=token.col_offset + 1,
                )


class SimilarVariableChecker(VisitorChecker):
    """Checker for finding same variables with similar names."""

    reports = ("possible-variable-overwriting",)

    def __init__(self):
        self.variables = defaultdict(set)
        self.parent_name = ""
        self.parent_type = ""
        super().__init__()

    def visit_Keyword(self, node):  # noqa
        self.variables = defaultdict(set)
        self.parent_name = node.name
        self.parent_type = type(node).__name__
        self.visit_vars_and_find_similar(node)
        self.generic_visit(node)

    visit_TestCase = visit_Keyword

    def visit_KeywordCall(self, node):  # noqa
        tokens = node.get_tokens(Token.ASSIGN)
        self.find_similar_variables(tokens, node)

    def visit_For(self, node):  # noqa
        for var in node.variables:
            self.variables[normalize_robot_var_name(var)].add(var)
        self.generic_visit(node)

    visit_ForLoop = visit_For

    def visit_vars_and_find_similar(self, node):
        """
        Creates a dictionary `variables` with normalized variable name as a key
        and ads a list of all detected variations of this variable in the node as a value,
        then it checks if similar variable was found.
        """
        for child in node.body:
            # read arguments from Test Case or Keyword
            if isinstance(child, Arguments):
                for token in child.get_tokens(Token.ARGUMENT):
                    self.variables[normalize_robot_var_name(token.value)].add(
                        token.value
                    )

    def find_similar_variables(self, tokens, node):
        for token in tokens:
            normalized_token = normalize_robot_var_name(token.value)
            if (
                normalized_token in self.variables
                and token.value not in self.variables[normalized_token]
            ):
                self.report(
                    "possible-variable-overwriting",
                    variable_name=token.value,
                    block_name=self.parent_name,
                    block_type=self.parent_type,
                    node=node,
                    lineno=token.lineno,
                    col=token.col_offset,
                )
            self.variables[normalized_token].add(token.value)


class DeprecatedStatementChecker(VisitorChecker):
    """Checker for deprecated statements."""

    reports = ("deprecated-statement", "deprecated-with-name")
    deprecated_keywords = {
        5: {
            "runkeywordunless": "IF",
            "runkeywordif": "IF",
            "exitforloop": "BREAK",
            "exitforloopif": "IF and BREAK",
            "continueforloop": "CONTINUE",
            "continueforloopif": "IF and CONTINUE",
            "returnfromkeyword": "RETURN",
            "returnfromkeywordif": "IF and RETURN",
        },
    }

    def visit_KeywordCall(self, node):  # noqa
        self.check_if_keyword_is_deprecated(node.keyword, node)

    def visit_SuiteSetup(self, node):  # noqa
        self.check_if_keyword_is_deprecated(node.name, node)

    visit_TestSetup = (
        visit_Setup
    ) = visit_SuiteTeardown = visit_TestTeardown = visit_Teardown = visit_SuiteSetup

    def visit_Return(self, node):  # noqa
        """For RETURN use visit_ReturnStatement - visit_Return will most likely visit RETURN in the future"""
        if ROBOT_VERSION.major < 5:
            return
        self.report(
            "deprecated-statement",
            statement_name="[Return]",
            alternative="RETURN",
            node=node,
            col=token_col(node, Token.RETURN),
            version="5.*",
        )

    def check_if_keyword_is_deprecated(self, keyword_name, node):
        normalized_keyword_name = normalize_robot_name(
            keyword_name, remove_prefix="builtin."
        )
        deprecated_statements = self.deprecated_keywords.get(ROBOT_VERSION.major, {})
        if normalized_keyword_name in deprecated_statements:
            alternative = deprecated_statements[normalized_keyword_name]
            col = token_col(node, Token.NAME, Token.KEYWORD)
            self.report(
                "deprecated-statement",
                statement_name=keyword_name,
                alternative=alternative,
                node=node,
                col=col,
                version=f"{ROBOT_VERSION.major}.*",
            )

    def visit_LibraryImport(self, node):  # noqa
        if ROBOT_VERSION.major < 5 or (
            ROBOT_VERSION.major == 5 and ROBOT_VERSION.minor == 0
        ):
            return
        with_name_token = node.get_token(Token.WITH_NAME)
        if not with_name_token or with_name_token.value == "AS":
            return
        self.report(
            "deprecated-with-name",
            node=with_name_token,
            col=with_name_token.col_offset + 1,
        )
