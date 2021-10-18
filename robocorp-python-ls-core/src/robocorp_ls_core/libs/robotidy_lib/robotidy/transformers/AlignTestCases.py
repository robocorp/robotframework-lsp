from robot.api.parsing import (
    ModelTransformer,
    Token,
    EmptyLine,
    Comment,
    ModelVisitor,
    ForHeader,
    End,
    IfHeader,
    ElseHeader,
    ElseIfHeader,
)

from robotidy.decorators import check_start_end_line
from robotidy.utils import round_to_four, is_suite_templated


class AlignTestCases(ModelTransformer):
    """
    Align Test Cases to columns.

    Currently only templated tests are supported. Following code:

        *** Test Cases ***    baz    qux
        # some comment
        test1    hi    hello
        test2 long test name    asdfasdf    asdsdfgsdfg

    will be transformed to:

        *** Test Cases ***      baz         qux
        # some comment
        test1                   hi          hello
        test2 long test name    asdfasdf    asdsdfgsdfg
                                bar1        bar2

    If you don't want to align test case section that does not contain header names (in above example baz and quz are
    header names) then configure `only_with_headers` parameter:

        robotidy -c AlignSettingsSection:only_with_hedaers:True <src>

    Supports global formatting params: ``--startline``, ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/AlignTestCases.html for more examples.
    """

    ENABLED = False

    def __init__(self, only_with_headers: bool = False):
        self.only_with_headers = only_with_headers
        self.templated = False
        self.widths = None
        self.test_name_len = 0
        self.name_line = 0
        self.indent = 0

    def visit_File(self, node):  # noqa
        if not is_suite_templated(node):
            return node
        return self.generic_visit(node)

    def visit_If(self, node):  # noqa
        self.indent += 1
        self.generic_visit(node)
        self.indent -= 1
        return node

    def visit_Else(self, node):  # noqa
        self.indent += 1
        self.generic_visit(node)
        self.indent -= 1
        return node

    def visit_ElseIf(self, node):  # noqa
        self.indent += 1
        self.generic_visit(node)
        self.indent -= 1
        return node

    def visit_For(self, node):  # noqa
        self.indent += 1
        self.generic_visit(node)
        self.indent -= 1
        return node

    @check_start_end_line
    def visit_TestCaseSection(self, node):  # noqa
        if len(node.header.data_tokens) == 1 and self.only_with_headers:
            return node
        counter = ColumnWidthCounter(self.formatting_config)
        counter.visit(node)
        self.widths = counter.widths
        return self.generic_visit(node)

    @check_start_end_line
    def visit_Statement(self, statement):  # noqa
        if statement.type == Token.TESTCASE_NAME:
            self.test_name_len = len(statement.tokens[0].value)
            self.name_line = statement.lineno
        elif statement.type == Token.TESTCASE_HEADER:
            self.align_header(statement)
        elif not isinstance(
            statement,
            (Comment, EmptyLine, ForHeader, IfHeader, ElseHeader, ElseIfHeader, End),
        ):
            self.align_statement(statement)
        return statement

    def align_header(self, statement):
        tokens = []
        for index, token in enumerate(statement.data_tokens[:-1]):
            tokens.append(token)
            separator = (self.widths[index] - len(token.value) + 4) * " "
            tokens.append(Token(Token.SEPARATOR, separator))
        tokens.append(statement.data_tokens[-1])
        tokens.append(statement.tokens[-1])  # eol
        statement.tokens = tokens
        return statement

    def align_statement(self, statement):
        tokens = []
        for line in statement.lines:
            strip_line = [t for t in line if t.type not in (Token.SEPARATOR, Token.EOL)]
            line_pos = 0
            exp_pos = 0
            widths = self.get_widths(statement)
            for token, width in zip(strip_line, widths):
                exp_pos += width + 4
                if self.test_name_len:
                    if self.name_line == statement.lineno:
                        exp_pos -= self.test_name_len
                    self.test_name_len = 0
                tokens.append(Token(Token.SEPARATOR, (exp_pos - line_pos) * " "))
                tokens.append(token)
                line_pos += len(token.value) + exp_pos - line_pos
            tokens.append(line[-1])
        statement.tokens = tokens

    def get_widths(self, statement):
        indent = self.indent
        if isinstance(statement, (ForHeader, End, IfHeader, ElseHeader, ElseIfHeader)):
            indent -= 1
        if not indent:
            return self.widths
        return [max(width, indent * 4) for width in self.widths]

    def visit_SettingSection(self, node):  # noqa
        return node

    def visit_VariableSection(self, node):  # noqa
        return node

    def visit_KeywordSection(self, node):  # noqa
        return node

    def visit_CommentSection(self, node):  # noqa
        return node


class ColumnWidthCounter(ModelVisitor):
    def __init__(self, formatting_config):
        self.widths = []
        self.formatting_config = formatting_config
        self.test_name_lineno = -1
        self.any_one_line_test = False
        self.header_with_cols = False

    def visit_TestCaseSection(self, node):  # noqa
        self.generic_visit(node)
        if not self.header_with_cols and not self.any_one_line_test and self.widths:
            self.widths[0] = 0
        self.widths = [round_to_four(length) for length in self.widths]

    @check_start_end_line
    def visit_Statement(self, statement):  # noqa
        if statement.type == Token.COMMENT:
            return
        if statement.type == Token.TESTCASE_HEADER:
            if len(statement.data_tokens) > 1:
                self.header_with_cols = True
                self._count_widths_from_statement(statement)
        elif statement.type == Token.TESTCASE_NAME:
            if self.widths:
                self.widths[0] = max(self.widths[0], len(statement.name))
            else:
                self.widths.append(len(statement.name))
            self.test_name_lineno = statement.lineno
        else:
            if self.test_name_lineno == statement.lineno:
                self.any_one_line_test = True
            if not isinstance(statement, (ForHeader, IfHeader, ElseHeader, ElseIfHeader, End)):
                self._count_widths_from_statement(statement, indent=1)

    def _count_widths_from_statement(self, statement, indent=0):
        for line in statement.lines:
            line = [t for t in line if t.type not in (Token.SEPARATOR, Token.EOL)]
            for index, token in enumerate(line, start=indent):
                if index < len(self.widths):
                    self.widths[index] = max(self.widths[index], len(token.value))
                else:
                    self.widths.append(len(token.value))
