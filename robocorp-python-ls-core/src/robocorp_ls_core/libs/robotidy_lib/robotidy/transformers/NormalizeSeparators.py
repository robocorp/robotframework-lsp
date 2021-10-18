from itertools import takewhile

import click
from robot.api.parsing import ModelTransformer, Token

from robotidy.decorators import check_start_end_line


class NormalizeSeparators(ModelTransformer):
    """
    Normalize separators and indents.

    All separators (pipes included) are converted to fixed length of 4 spaces (configurable via global argument
    ``--spacecount``).

    You can decide which sections should be transformed by configuring
    ``sections = comments,settings,variables,keywords,testcases`` param.

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/NormalizeSeparators.html for more examples.
    """

    def __init__(self, sections: str = None):
        self.indent = 0
        self.sections = self.parse_sections(sections)

    @staticmethod
    def parse_sections(sections):
        default = {"comments", "settings", "testcases", "keywords", "variables"}
        if sections is None:
            return default
        if not sections:
            return {}
        parts = sections.split(",")
        parsed_sections = set()
        for part in parts:
            part = part.replace("_", "")
            if part and part[-1] != "s":
                part += "s"
            if part not in default:
                raise click.BadOptionUsage(
                    option_name="transform",
                    message=f"Invalid configurable value: '{sections}' for sections for NormalizeSeparators transformer."
                    f" Sections to be transformed should be provided in comma separated list with valid section"
                    f" names:\n{sorted(default)}",
                )
            parsed_sections.add(part)
        return parsed_sections

    def visit_File(self, node):  # noqa
        self.indent = 0
        return self.generic_visit(node)

    def should_visit(self, name, node):
        if name in self.sections:
            return self.generic_visit(node)
        return node

    def visit_CommentSection(self, node):  # noqa
        return self.should_visit("comments", node)

    def visit_SettingSection(self, node):  # noqa
        return self.should_visit("settings", node)

    def visit_VariableSection(self, node):  # noqa
        return self.should_visit("variables", node)

    def visit_KeywordSection(self, node):  # noqa
        return self.should_visit("keywords", node)

    def visit_TestCaseSection(self, node):  # noqa
        return self.should_visit("testcases", node)

    def visit_TestCase(self, node):  # noqa
        self.visit_Statement(node.header)
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        return node

    def visit_Keyword(self, node):  # noqa
        self.visit_Statement(node.header)
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        return node

    def visit_For(self, node):
        self.visit_Statement(node.header)
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        self.visit_Statement(node.end)
        return node

    def visit_If(self, node):
        self.visit_Statement(node.header)
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        if node.orelse:
            self.visit(node.orelse)
        if node.end:
            self.visit_Statement(node.end)
        return node

    @check_start_end_line
    def visit_Statement(self, statement):  # noqa
        has_pipes = statement.tokens[0].value.startswith("|")
        return self._handle_spaces(statement, has_pipes)

    def _handle_spaces(self, statement, has_pipes):
        new_tokens = []
        for line in statement.lines:
            if has_pipes and len(line) > 1:
                line = self._remove_consecutive_separators(line)
            new_tokens.extend([self._normalize_spaces(i, t, len(line)) for i, t in enumerate(line)])
        statement.tokens = new_tokens
        self.generic_visit(statement)
        return statement

    @staticmethod
    def _remove_consecutive_separators(line):
        sep_count = len(list(takewhile(lambda t: t.type == Token.SEPARATOR, line)))
        return line[sep_count - 1 :]

    def _normalize_spaces(self, index, token, line_length):
        if token.type == Token.SEPARATOR:
            count = self.indent if index == 0 else 1
            token.value = self.formatting_config.separator * count
        # remove trailing whitespace from last token
        if index == line_length - 2:
            token.value = token.value.rstrip()
        return token
