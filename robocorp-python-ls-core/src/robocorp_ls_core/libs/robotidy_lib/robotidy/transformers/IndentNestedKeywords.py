from robot.api.parsing import Token

from robotidy.disablers import skip_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.skip import Skip
from robotidy.transformers import Transformer
from robotidy.transformers.run_keywords import get_run_keywords
from robotidy.utils import (
    collect_comments_from_tokens,
    get_new_line,
    is_token_value_in_tokens,
    join_tokens_with_token,
    merge_comments_into_one,
    normalize_name,
    split_on_token_type,
    split_on_token_value,
)


class IndentNestedKeywords(Transformer):
    """
    Format indentation inside run keywords variants such as ``Run Keywords`` or
    ``Run Keyword And Continue On Failure``.

    Keywords inside run keywords variants are detected and
    whitespace is formatted to outline them. This code:

    ```robotframework
        Run Keyword    Run Keyword If    ${True}    Run keywords   Log    foo    AND    Log    bar    ELSE    Log    baz
    ```

    will be transformed to:

    ```robotframework
        Run Keyword
        ...    Run Keyword If    ${True}
        ...        Run keywords
        ...            Log    foo
        ...            AND
        ...            Log    bar
        ...    ELSE
        ...        Log    baz
    ```

    ``AND`` argument inside ``Run Keywords`` can be handled in different ways. It is controlled via ``indent_and``
    parameter. For more details see the full documentation.

    To skip formatting run keywords inside settings (such as ``Suite Setup``, ``[Setup]``, ``[Teardown]`` etc.) set
    ``skip_settings`` to ``True``.
    """

    ENABLED = False
    HANDLES_SKIP = frozenset({"skip_settings"})

    def __init__(self, indent_and: str = "split", skip: Skip = None):
        super().__init__(skip=skip)
        self.indent_and = indent_and
        self.validate_indent_and()
        self.run_keywords = get_run_keywords()

    def validate_indent_and(self):
        modes = {"keep_in_line", "split", "split_and_indent"}
        if self.indent_and not in modes:
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "indent_and",
                self.indent_and,
                f"Select one of: {','.join(modes)}",
            )

    def get_run_keyword(self, kw_name):
        kw_norm = normalize_name(kw_name)
        return self.run_keywords.get(kw_norm, None)

    def get_setting_lines(self, node):  # noqa
        if self.skip.setting("any") or node.errors or not len(node.data_tokens) > 1:
            return None
        run_keyword = self.get_run_keyword(node.data_tokens[1].value)
        if not run_keyword:
            return None
        return self.parse_sub_kw(node.data_tokens[1:])

    def get_separator(self, column=1, continuation=False):
        if continuation:
            separator = self.formatting_config.continuation_indent * column
        else:
            separator = self.formatting_config.separator * column
        return Token(Token.SEPARATOR, separator)

    def parse_keyword_lines(self, lines, tokens, new_line, eol):
        separator = self.get_separator()
        for column, line in lines[1:]:
            tokens.extend(new_line)
            tokens.append(self.get_separator(column, True))
            tokens.extend(join_tokens_with_token(line, separator))
        tokens.append(eol)
        return tokens

    @skip_if_disabled
    def visit_SuiteSetup(self, node):  # noqa
        lines = self.get_setting_lines(node)
        if not lines:
            return node
        comments = collect_comments_from_tokens(node.tokens, indent=None)
        separator = self.get_separator()
        new_line = get_new_line()
        tokens = [node.data_tokens[0], separator, *join_tokens_with_token(lines[0][1], separator)]
        node.tokens = self.parse_keyword_lines(lines, tokens, new_line, eol=node.tokens[-1])
        return (*comments, node)

    visit_SuiteTeardown = visit_TestSetup = visit_TestTeardown = visit_SuiteSetup

    @skip_if_disabled
    def visit_Setup(self, node):  # noqa
        lines = self.get_setting_lines(node)
        if not lines:
            return node
        indent = node.tokens[0]
        separator = self.get_separator()
        new_line = get_new_line(indent)
        tokens = [indent, node.data_tokens[0], separator, *join_tokens_with_token(lines[0][1], separator)]
        comment = merge_comments_into_one(node.tokens)
        if comment:
            # need to add comments on first line for [Setup] / [Teardown] settings
            comment_sep = Token(Token.SEPARATOR, "  ")
            tokens.extend([comment_sep, Token(Token.COMMENT, comment)])
        node.tokens = self.parse_keyword_lines(lines, tokens, new_line, eol=node.tokens[-1])
        return node

    visit_Teardown = visit_Setup

    @skip_if_disabled
    def visit_KeywordCall(self, node):  # noqa
        if node.errors or not node.keyword:
            return node
        run_keyword = self.get_run_keyword(node.keyword)
        if not run_keyword:
            return node

        indent = node.tokens[0]
        comments = collect_comments_from_tokens(node.tokens, indent)
        assign, kw_tokens = split_on_token_type(node.data_tokens, Token.KEYWORD)
        lines = self.parse_sub_kw(kw_tokens)
        if not lines:
            return node

        separator = self.get_separator()
        tokens = [indent]
        if assign:
            tokens.extend([*join_tokens_with_token(assign, separator), separator])
        tokens.extend(join_tokens_with_token(lines[0][1], separator))
        new_line = get_new_line(indent)
        node.tokens = self.parse_keyword_lines(lines, tokens, new_line, eol=node.tokens[-1])
        return (*comments, node)

    def parse_sub_kw(self, tokens, column=0):
        if not tokens:
            return []
        run_keyword = self.get_run_keyword(tokens[0].value)
        if not run_keyword:
            return [(column, list(tokens))]
        lines = [(column, tokens[: run_keyword.resolve])]
        tokens = tokens[run_keyword.resolve :]
        if run_keyword.branches:
            if "ELSE IF" in run_keyword.branches:
                while is_token_value_in_tokens("ELSE IF", tokens):
                    column = max(column, 1)
                    prefix, branch, tokens = split_on_token_value(tokens, "ELSE IF", 2)
                    lines.extend(self.parse_sub_kw(prefix, column + 1))
                    lines.append((column, branch))
            if "ELSE" in run_keyword.branches and is_token_value_in_tokens("ELSE", tokens):
                return self.split_on_else(tokens, lines, column)
        elif run_keyword.split_on_and:
            return self.split_on_and(tokens, lines, column)
        return lines + self.parse_sub_kw(tokens, column + 1)

    def split_on_else(self, tokens, lines, column):
        column = max(column, 1)
        prefix, branch, tokens = split_on_token_value(tokens, "ELSE", 1)
        lines.extend(self.parse_sub_kw(prefix, column + 1))
        lines.append((column, branch))
        lines.extend(self.parse_sub_kw(tokens, column + 1))
        return lines

    def split_on_and(self, tokens, lines, column):
        if is_token_value_in_tokens("AND", tokens):
            while is_token_value_in_tokens("AND", tokens):
                prefix, branch, tokens = split_on_token_value(tokens, "AND", 1)
                if self.indent_and == "keep_in_line":
                    lines.extend(self.parse_sub_kw(prefix + branch, column + 1))
                else:
                    indent = int(self.indent_and == "split_and_indent")  # indent = 1 for split_and_indent, else 0
                    lines.extend(self.parse_sub_kw(prefix, column + 1 + indent))
                    lines.append((column + 1, branch))
            indent = int(self.indent_and == "split_and_indent")  # indent = 1 for split_and_indent, else 0
            lines.extend(self.parse_sub_kw(tokens, column + 1 + indent))
        else:
            lines.extend([(column + 1, [kw_token]) for kw_token in tokens])
        return lines
