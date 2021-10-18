from typing import Optional

from robot.api.parsing import ModelTransformer, EmptyLine, Token

from robotidy.utils import is_suite_templated


class NormalizeNewLines(ModelTransformer):
    """
    Normalize new lines.

    Ensure that there is exactly:
    - ``section_lines = 1`` empty lines between sections,
    - ``test_case_lines = 1`` empty lines between test cases,
    - ``keyword_lines = test_case_lines`` empty lines between keywords.

    Removes empty lines after section (and before any data) and appends 1 empty line at the end of file.

    Consecutive empty lines inside settings, variables, keywords and test cases are also removed
    (configurable via ``consecutive_lines = 1``). If set to 0 all empty lines will be removed.

    If the suite contains Test Template tests will not be separated by empty lines unless ``separate_templated_tests``
    is set to True.

    See https://robotidy.readthedocs.io/en/latest/transformers/NormalizeNewLines.html for more examples.
    """

    def __init__(
        self,
        test_case_lines: int = 1,
        keyword_lines: Optional[int] = None,
        section_lines: int = 1,
        separate_templated_tests: bool = False,
        consecutive_lines: int = 1,
    ):
        self.test_case_lines = test_case_lines
        self.keyword_lines = keyword_lines if keyword_lines is not None else test_case_lines
        self.section_lines = section_lines
        self.separate_templated_tests = separate_templated_tests
        self.consecutive_lines = consecutive_lines
        self.last_section = None
        self.last_test = None
        self.last_keyword = None
        self.templated = False

    def visit_File(self, node):  # noqa
        self.templated = not self.separate_templated_tests and is_suite_templated(node)
        self.last_section = node.sections[-1] if node.sections else None
        return self.generic_visit(node)

    def visit_Section(self, node):  # noqa
        self.trim_empty_lines(node)
        empty_line = EmptyLine.from_params()
        if node is self.last_section:
            return self.generic_visit(node)
        node.body.extend([empty_line] * self.section_lines)
        return self.generic_visit(node)

    def visit_TestCaseSection(self, node):  # noqa
        self.last_test = node.body[-1] if node.body else None
        return self.visit_Section(node)

    def visit_KeywordSection(self, node):  # noqa
        self.last_keyword = node.body[-1] if node.body else None
        return self.visit_Section(node)

    def visit_TestCase(self, node):  # noqa
        self.trim_empty_lines(node)
        if node is not self.last_test and not self.templated:
            node.body.extend([EmptyLine.from_params()] * self.test_case_lines)
        return self.generic_visit(node)

    def visit_Keyword(self, node):  # noqa
        self.trim_empty_lines(node)
        if node is not self.last_keyword:
            node.body.extend([EmptyLine.from_params()] * self.keyword_lines)
        return self.generic_visit(node)

    def visit_Statement(self, node):  # noqa
        tokens = []
        for line in node.lines:
            if line[-1].type == Token.EOL:
                line[-1].value = "\n"  # TODO: use global formatting in the future
            tokens.extend(line)
        node.tokens = tokens
        return node

    def trim_empty_lines(self, node):
        self.trim_leading_empty_lines(node)
        self.trim_trailing_empty_lines(node)
        self.trim_consecutive_empty_lines(node)

    @staticmethod
    def trim_trailing_empty_lines(node):
        if not hasattr(node, "body"):
            return
        while node.body and isinstance(node.body[-1], EmptyLine):
            node.body.pop()

    @staticmethod
    def trim_leading_empty_lines(node):
        while node.body and isinstance(node.body[0], EmptyLine):
            node.body.pop(0)

    def trim_consecutive_empty_lines(self, node):
        empty_count = 0
        nodes = []
        for child in node.body:
            if isinstance(child, EmptyLine):
                empty_count += 1
            else:
                empty_count = 0
            if empty_count <= self.consecutive_lines:
                nodes.append(child)
        node.body = nodes
