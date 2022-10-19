from robot.api.parsing import EmptyLine, SectionHeader, Token
from robot.parsing.model.statements import Statement

from robotidy.exceptions import InvalidParameterValueError

try:
    from robot.api.parsing import InlineIfHeader
except ImportError:
    InlineIfHeader = None
from robotidy.transformers import Transformer


class MergeAndOrderSections(Transformer):
    """
    Merge duplicated sections and order them.

    Default order is: Comments > Settings > Variables > Test Cases > Keywords.

    You can change sorting order by configuring ``order`` parameter with comma separated list of section names (without
    spaces):

    ```
    robotidy --transform MergeAndOrderSections:order=settings,keywords,variables,testcases,comments
    ```

    Because merging and changing the order of sections can shuffle your empty lines it's greatly advised to always
    run ``NormalizeNewLines`` transformer after this one.

    If both ``*** Test Cases ***`` and ``*** Tasks ***`` are defined in one file they will be merged into one (header
    name will be taken from first encountered section).

    Any data before first section is treated as comment in Robot Framework. This transformer add ``*** Comments ***``
    section for such lines:

    ```robotframework
    i am comment
    # robocop: disable
    *** Settings ***
    ```

    To:

    ```robotframework
    *** Comments ***
    i am comment
    # robocop: disable
    *** Settings ***
    ```

    You can disable this behaviour by setting ``create_comment_section`` to False.
    """

    def __init__(self, order: str = "", create_comment_section: bool = True):
        super().__init__()
        self.sections_order = self.parse_order(order)
        self.create_comment_section = create_comment_section

    def parse_order(self, order):
        default_order = (
            Token.COMMENT_HEADER,
            Token.SETTING_HEADER,
            Token.VARIABLE_HEADER,
            Token.TESTCASE_HEADER,
            Token.KEYWORD_HEADER,
        )
        if not order:
            return default_order
        parts = order.lower().split(",")
        map = {
            "comments": Token.COMMENT_HEADER,
            "comment": Token.COMMENT_HEADER,
            "settings": Token.SETTING_HEADER,
            "setting": Token.SETTING_HEADER,
            "variables": Token.VARIABLE_HEADER,
            "variable": Token.VARIABLE_HEADER,
            "testcases": Token.TESTCASE_HEADER,
            "testcase": Token.TESTCASE_HEADER,
            "keywords": Token.KEYWORD_HEADER,
            "keyword": Token.KEYWORD_HEADER,
        }
        parsed_order = []
        for part in parts:
            parsed_order.append(map.get(part, None))
        if any(header not in parsed_order for header in default_order) and len(parsed_order) != len(default_order):
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "order",
                order,
                "Custom order should be provided in comma separated list with all section names:\n"
                "order=comments,settings,variables,testcases,variables",
            )
        return parsed_order

    def visit_File(self, node):  # noqa
        if len(node.sections) < 2:
            return node
        sections = {}
        last = len(node.sections) - 1
        for index, section in enumerate(node.sections):
            if index == last:
                section = self.from_last_section(section)
            section_type = self.get_section_type(section)
            if section_type not in sections:
                sections[section_type] = section
            else:
                if len(section.header.data_tokens) > 1:
                    print(
                        f"{node.source}: Merged duplicated section has section header comments. "
                        "Only header comments from first section header of the same type are preserved."
                    )
                sections[section_type].body += section.body
        node.sections = [sections[order] for order in self.sections_order if order in sections]
        return node

    @staticmethod
    def normalize_eol(tokens):
        new_tokens = []
        for tok in tokens:
            if tok.type == Token.EOL:
                tok.value = "\n"
            new_tokens.append(tok)
        return new_tokens

    def from_last_section(self, node):
        """Last node use different logic for new line marker. It is not possible to preserve all empty lines but
        we need at least ensure that following code::

             *** Test Case ***
             *** Variables ***

        Will not become::
            *** Variables ****** Test Case ***

        """
        # Empty sections, just *** Test Cases *** etc
        if not node.body:
            node.header.tokens = self.normalize_eol(node.header.tokens)
            return node

        # Settings, Variables or Comments
        if not hasattr(node.body[-1], "body"):
            node.body[-1].tokens = self.normalize_eol(node.body[-1].tokens)
            return node

        # Last keyword or test case
        if not node.body[-1].body:
            node.body[-1].body.append(EmptyLine.from_params())
            return node

        last_statement = node.body[-1].body[-1]
        if hasattr(last_statement, "end"):
            if (
                InlineIfHeader
                and hasattr(last_statement, "header")
                and isinstance(last_statement.header, InlineIfHeader)
            ):
                if not last_statement.errors:
                    node.body[-1].body[-1].body[-1].tokens = self.normalize_eol(last_statement.body[-1].tokens)
                return node
            if last_statement.end:  # not end if parsing errors
                node.body[-1].body[-1].end.tokens = self.normalize_eol(last_statement.end.tokens)
        else:
            node.body[-1].body[-1] = Statement.from_tokens(self.normalize_eol(last_statement.tokens))
        return node

    def get_section_type(self, section):
        header_tokens = (
            Token.COMMENT_HEADER,
            Token.TESTCASE_HEADER,
            Token.SETTING_HEADER,
            Token.KEYWORD_HEADER,
            Token.VARIABLE_HEADER,
        )
        if section.header:
            name_token = section.header.get_token(*header_tokens)
            section_type = name_token.type
        else:
            section_type = Token.COMMENT_HEADER
            if self.create_comment_section:
                section.header = SectionHeader.from_params(section_type, "*** Comments ***")
        return section_type
