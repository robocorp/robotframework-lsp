from robot.api.parsing import Comment, EmptyLine

try:
    from robot.api.parsing import ReturnStatement
except ImportError:
    ReturnStatement = None

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.transformers import Transformer
from robotidy.utils import (
    after_last_dot,
    create_statement_from_tokens,
    normalize_name,
    wrap_in_if_and_replace_statement,
)


class ReplaceReturns(Transformer):
    """
    Replace return statements (such as [Return] setting or Return From Keyword keyword) with RETURN statement.

    Following code:

    ```robotframework
    *** Keywords ***
    Keyword
        Return From Keyword If    $condition    2
        Sub Keyword
        [Return]    1

    Keyword 2
        Return From Keyword    ${arg}
    ```

    will be transformed to:

    ```robotframework
    *** Keywords ***
    Keyword
        IF    $condition
            RETURN    2
        END
        Sub Keyword
        RETURN    1

    Keyword 2
        RETURN    ${arg}
    ```
    """

    MIN_VERSION = 5

    def __init__(self):
        super().__init__()
        self.return_statement = None

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def visit_Keyword(self, node):  # noqa
        self.return_statement = None
        node = self.generic_visit(node)
        if self.return_statement:
            skip_lines = []
            indent = self.return_statement.tokens[0]
            while node.body and isinstance(node.body[-1], (EmptyLine, Comment)):
                skip_lines.append(node.body.pop())
            return_stmt = create_statement_from_tokens(
                statement=ReturnStatement, tokens=self.return_statement.tokens[2:], indent=indent
            )
            node.body.append(return_stmt)
            node.body.extend(skip_lines)
        return node

    @skip_if_disabled
    def visit_KeywordCall(self, node):  # noqa
        if not node.keyword or node.errors:
            return node
        normalized_name = after_last_dot(normalize_name(node.keyword))
        if normalized_name == "returnfromkeyword":
            return create_statement_from_tokens(
                statement=ReturnStatement, tokens=node.tokens[2:], indent=node.tokens[0]
            )
        elif normalized_name == "returnfromkeywordif":
            return wrap_in_if_and_replace_statement(node, ReturnStatement, self.formatting_config.separator)
        return node

    @skip_if_disabled
    def visit_Return(self, node):  # noqa
        self.return_statement = node

    @skip_if_disabled
    def visit_Error(self, node):  # noqa
        """Remove duplicate [Return]"""
        for error in node.errors:
            if "Setting 'Return' is allowed only once" in error:
                return None
        return node
