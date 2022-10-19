from robot.api.parsing import KeywordCall, Token

try:
    from robot.api.parsing import InlineIfHeader, ReturnStatement
except ImportError:
    InlineIfHeader = None
    ReturnStatement = None

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.skip import Skip
from robotidy.transformers import Transformer


class NormalizeSeparators(Transformer):
    """
    Normalize separators and indents.

    All separators (pipes included) are converted to fixed length of 4 spaces (configurable via global argument
    ``--spacecount``).

    You can decide which sections should be transformed by configuring
    ``sections = comments,settings,variables,keywords,testcases`` param.

    To not format documentation configure ``skip_documentation`` to ``True``.
    """

    HANDLES_SKIP = frozenset(
        {"skip_documentation", "skip_keyword_call", "skip_keyword_call_pattern", "skip_comments", "skip_block_comments"}
    )

    def __init__(self, sections: str = None, skip: Skip = None):
        super().__init__(skip=skip)
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

    @skip_section_if_disabled
    def visit_CommentSection(self, node):  # noqa
        return self.should_visit("comments", node)

    @skip_section_if_disabled
    def visit_SettingSection(self, node):  # noqa
        return self.should_visit("settings", node)

    @skip_section_if_disabled
    def visit_VariableSection(self, node):  # noqa
        return self.should_visit("variables", node)

    @skip_section_if_disabled
    def visit_KeywordSection(self, node):  # noqa
        return self.should_visit("keywords", node)

    @skip_section_if_disabled
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
        self.indent += 1
        node.body = [self.visit(item) for item in node.body]
        self.indent -= 1
        if node.orelse:
            self.visit(node.orelse)
        if node.end:
            self.visit_Statement(node.end)
        self.is_inline = False
        return node

    def visit_Documentation(self, doc):  # noqa
        if self.skip.documentation:
            has_pipes = doc.tokens[0].value.startswith("|")
            return self._handle_spaces(doc, has_pipes, only_indent=True)
        return self.visit_Statement(doc)

    def visit_KeywordCall(self, keyword):  # noqa
        if self.skip.keyword_call(keyword):
            return keyword
        return self.visit_Statement(keyword)

    def visit_Comment(self, node):  # noqa
        if self.skip.comment(node):
            return node
        return self.visit_Statement(node)

    def is_keyword_inside_inline_if(self, node):
        return self.is_inline and (
            isinstance(node, KeywordCall) or ReturnStatement and isinstance(node, ReturnStatement)
        )

    @skip_if_disabled
    def visit_Statement(self, statement):  # noqa
        if statement is None:
            return None
        has_pipes = statement.tokens[0].value.startswith("|")
        return self._handle_spaces(statement, has_pipes)

    def _handle_spaces(self, statement, has_pipes, only_indent=False):
        new_tokens = []
        prev_token = None
        for line in statement.lines:
            prev_sep = False
            for index, token in enumerate(line):
                if token.type == Token.SEPARATOR:
                    if prev_sep:
                        continue
                    prev_sep = True
                    if index == 0 and not self.is_keyword_inside_inline_if(statement):
                        token.value = self.formatting_config.indent * self.indent
                    elif not only_indent:
                        if prev_token and prev_token.type == Token.CONTINUATION:
                            token.value = self.formatting_config.continuation_indent
                        else:
                            token.value = self.formatting_config.separator
                else:
                    prev_sep = False
                    prev_token = token
                if has_pipes and index == len(line) - 2:
                    token.value = token.value.rstrip()
                new_tokens.append(token)
        statement.tokens = new_tokens
        self.generic_visit(statement)
        return statement
