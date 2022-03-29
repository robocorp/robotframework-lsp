from typing import Iterable

from robot.api.parsing import ModelTransformer, Token

try:
    from robot.api.parsing import Continue, Break
except ImportError:
    Continue, Break = None, None

from robotidy.utils import normalize_name, after_last_dot, wrap_in_if_and_replace_statement, ROBOT_VERSION
from robotidy.decorators import check_start_end_line


class ReplaceBreakContinue(ModelTransformer):
    """
    Replace Continue For Loop and Exit For Loop keyword variants with CONTINUE and BREAK statements.

    Following code:

        *** Keywords ***
        Keyword
            FOR    ${var}    IN  1  2
                Continue For Loop
                Continue For Loop If    $condition
                Exit For Loop
                Exit For Loop If    $condition
            END

    will be transformed to:

        *** Keywords ***
        Keyword
            FOR    ${var}    IN  1  2
                CONTINUE
                IF    $condition
                    CONTINUE
                END
                BREAK
                IF    $condition
                    BREAK
                END
            END

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/ReplaceBreakContinue.html for more examples.
    """

    ENABLED = ROBOT_VERSION.major >= 5

    def __init__(self):
        self.in_loop = False

    def visit_File(self, node):  # noqa
        self.in_loop = False
        return self.generic_visit(node)

    @staticmethod
    def create_statement_from_tokens(statement, tokens: Iterable, indent: Token):
        return statement([indent, Token(statement.type), *tokens])

    @check_start_end_line
    def visit_KeywordCall(self, node):  # noqa
        if not self.in_loop or not node.keyword or node.errors:
            return node
        normalized_name = after_last_dot(normalize_name(node.keyword))
        if "forloop" not in normalized_name:
            return node
        if normalized_name == "continueforloop":
            return self.create_statement_from_tokens(statement=Continue, tokens=node.tokens[2:], indent=node.tokens[0])
        elif normalized_name == "exitforloop":
            return self.create_statement_from_tokens(statement=Break, tokens=node.tokens[2:], indent=node.tokens[0])
        elif normalized_name == "continueforloopif":
            return wrap_in_if_and_replace_statement(node, Continue, self.formatting_config.separator)
        elif normalized_name == "exitforloopif":
            return wrap_in_if_and_replace_statement(node, Break, self.formatting_config.separator)
        return node

    def visit_For(self, node):  # noqa
        self.in_loop = True
        node = self.generic_visit(node)
        self.in_loop = False
        return node

    visit_While = visit_For
