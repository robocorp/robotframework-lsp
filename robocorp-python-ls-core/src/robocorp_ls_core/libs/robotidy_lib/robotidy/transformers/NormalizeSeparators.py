from itertools import takewhile

from robot.api.parsing import ModelTransformer, Token

try:
    from robot.api.parsing import InlineIfHeader
except ImportError:
    InlineIfHeader = None

from robotidy.decorators import check_start_end_line
from robotidy.exceptions import InvalidParameterValueError


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
        self.is_inline = False

    def parse_sections(self, sections):
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
                raise InvalidParameterValueError(
                    self.__class__.__name__,
                    "sections",
                    sections,
                    f"Sections to be transformed should be provided in comma separated "
                    f"list with valid section names:\n{sorted(default)}",
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

    def indented_block(self, node):
        self.visit_Statement(node.header)
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        return node

    def visit_TestCase(self, node):  # noqa
        return self.indented_block(node)

    visit_Keyword = visit_While = visit_TestCase  # noqa

    def visit_For(self, node):
        node = self.indented_block(node)
        self.visit_Statement(node.end)
        return node

    def visit_Try(self, node):
        node = self.indented_block(node)
        if node.next:
            self.visit(node.next)
        if node.end:
            self.visit_Statement(node.end)
        return node

    def visit_If(self, node):
        if self.is_inline:  # nested inline if is ignored
            return node
        self.is_inline = InlineIfHeader and isinstance(node.header, InlineIfHeader)
        self.visit_Statement(node.header)
        indent = 1
        if self.is_inline:
            indent = self.indent
            self.indent = 1
        else:
            self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        if self.is_inline:
            self.indent = indent
        else:
            self.indent -= 1
        if node.orelse:
            self.visit(node.orelse)
        if node.end:
            self.visit_Statement(node.end)
        self.is_inline = False
        return node

    @check_start_end_line
    def visit_Statement(self, statement):  # noqa
        has_pipes = statement.tokens[0].value.startswith("|")
        return self._handle_spaces(statement, has_pipes)

    def _handle_spaces(self, statement, has_pipes):
        new_tokens = []
        for line in statement.lines:
            prev_sep = False
            for index, token in enumerate(line):
                if token.type == Token.SEPARATOR:
                    if prev_sep:
                        continue
                    prev_sep = True
                    count = self.indent if index == 0 else 1
                    token.value = self.formatting_config.separator * count
                else:
                    prev_sep = False
                if has_pipes and index == len(line) - 2:
                    token.value = token.value.rstrip()
                new_tokens.append(token)
        statement.tokens = new_tokens
        self.generic_visit(statement)
        return statement
