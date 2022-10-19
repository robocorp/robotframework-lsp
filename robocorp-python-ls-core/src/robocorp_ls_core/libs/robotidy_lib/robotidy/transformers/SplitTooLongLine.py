import re

from robot.api.parsing import Comment, Token

try:
    from robot.api.parsing import InlineIfHeader
except ImportError:
    InlineIfHeader = None
from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.skip import Skip
from robotidy.transformers import Transformer
from robotidy.utils import ROBOT_VERSION

EOL = Token(Token.EOL)
CONTINUATION = Token(Token.CONTINUATION)


class SplitTooLongLine(Transformer):
    """
    Split too long lines.
    If any line in the keyword call or variable exceeds given length limit (120 by default) it will be
    split:

    ```robotframework
    *** Keywords ***
    Keyword
        Keyword With Longer Name    ${arg1}    ${arg2}    ${arg3}  # let's assume that arg2 is at 120 char
    ```

    To:

    ```robotframework
    *** Keywords ***
    Keyword
        # let's assume that arg2 is at 120 char
        Keyword With Longer Name
        ...    ${arg1}
        ...    ${arg2}
        ...    ${arg3}
    ```

    Allowed line length is configurable using global parameter ``--line-length``:

    ```
    robotidy --line-length 140 src.robot
    ```

    Or using dedicated for this transformer parameter ``line_length``:

    ```
    robotidy --configure SplitTooLongLine:line_length:140 src.robot
    ```

    ``split_on_every_arg`` and ``split_on_every_value`` flags (``True`` by default) controls whether arguments
    and values are split or fills the line until character limit:

    ```robotframework
    *** Test Cases ***
    Test with default split_on_every_arg
        # ${arg1} fits under limit, so it stays in the line
        Keyword With Longer Name    ${arg1}
        ...    ${arg2}    ${arg3}

    Test with split_on_every_arg = False
        # arguments are split
        Keyword With Longer Name
        ...    ${arg1}
        ...    ${arg2}
        ...    ${arg3}
    ```

    Supports global formatting params: ``spacecount`` and ``separator``.
    """

    IGNORED_WHITESPACE = {Token.EOL, Token.CONTINUATION}
    HANDLES_SKIP = frozenset({"skip_keyword_call", "skip_keyword_call_pattern"})

    def __init__(
        self,
        line_length: int = None,
        split_on_every_arg: bool = True,
        split_on_every_value: bool = True,
        skip: Skip = None,
    ):
        super().__init__(skip)
        self._line_length = line_length
        self.split_on_every_arg = split_on_every_arg
        self.split_on_every_value = split_on_every_value
        self.robocop_disabler_pattern = re.compile(
            r"(# )+(noqa|robocop: ?(?P<disabler>disable|enable)=?(?P<rules>[\w\-,]*))"
        )

    @property
    def line_length(self):
        return self.formatting_config.line_length if self._line_length is None else self._line_length

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def visit_If(self, node):  # noqa
        if self.is_inline(node):
            return node
        if node.orelse:
            self.generic_visit(node.orelse)
        return self.generic_visit(node)

    @staticmethod
    def is_inline(node):
        return ROBOT_VERSION.major > 4 and isinstance(node.header, InlineIfHeader)

    def should_transform_node(self, node):
        if not self.any_line_too_long(node):
            return False
        # find if any line contains more than one data tokens - so we have something to split
        for line in node.lines:
            count = 0
            for token in line:
                if token.type not in Token.NON_DATA_TOKENS:
                    count += 1
                if count > 1:
                    return True
        return False

    def any_line_too_long(self, node):
        for line in node.lines:
            line = "".join(token.value for token in line)
            line = self.robocop_disabler_pattern.sub("", line)
            line = line.rstrip().expandtabs(4)
            if len(line) >= self.line_length:
                return True
        return False

    def visit_KeywordCall(self, node):  # noqa
        if self.skip.keyword_call(node):
            return node
        if not self.should_transform_node(node):
            return node
        if self.disablers.is_node_disabled(node, full_match=False):
            return node
        return self.split_keyword_call(node)

    @skip_if_disabled
    def visit_Variable(self, node):  # noqa
        if not self.should_transform_node(node):
            return node
        return self.split_variable_def(node)

    @staticmethod
    def join_on_separator(tokens, separator):
        for token in tokens:
            yield token
            yield separator

    @staticmethod
    def split_to_multiple_lines(tokens, indent, separator):
        first = True
        for token in tokens:
            yield indent
            if not first:
                yield CONTINUATION
                yield separator
            yield token
            yield EOL
            first = False

    def split_tokens(self, tokens, line, split_on, indent=None):
        separator = Token(Token.SEPARATOR, self.formatting_config.separator)
        cont_indent = Token(Token.SEPARATOR, self.formatting_config.continuation_indent)
        split_tokens, comments = [], []
        # Comments with separators inside them are split into
        # [COMMENT, SEPARATOR, COMMENT] tokens in the AST, so in order to preserve the
        # original comment, we need a lookback on the separator tokens.
        last_separator = None
        for token in tokens:
            if token.type in self.IGNORED_WHITESPACE:
                continue
            if token.type == Token.SEPARATOR:
                last_separator = token
            elif token.type == Token.COMMENT:
                # AST splits comments with separators, e.g.
                #
                # "# Comment     rest" -> ["# Comment", "     ", "rest"].
                #
                # Notice the third value not starting with a hash - that's what this
                # condition is about:
                if comments and not token.value.startswith("#"):
                    comments[-1].value += last_separator.value + token.value
                else:
                    comments.append(token)
            elif token.type == Token.ARGUMENT:
                if token.value == "":
                    token.value = "${EMPTY}"
                if split_on or not self.col_fit_in_line(line + [separator, token]):
                    line.append(EOL)
                    split_tokens.extend(line)
                    if indent:
                        line = [indent, CONTINUATION, cont_indent, token]
                    else:
                        line = [CONTINUATION, cont_indent, token]
                else:
                    line.extend([separator, token])
        split_tokens.extend(line)
        split_tokens.append(EOL)
        return split_tokens, comments

    def split_variable_def(self, node):
        line = [node.data_tokens[0]]
        tokens, comments = self.split_tokens(node.tokens, line, self.split_on_every_value)
        comments = [Comment([comment, EOL]) for comment in comments]
        node.tokens = tokens
        return (*comments, node)

    def split_keyword_call(self, node):
        separator = Token(Token.SEPARATOR, self.formatting_config.separator)
        cont_indent = Token(Token.SEPARATOR, self.formatting_config.continuation_indent)
        indent = node.tokens[0]

        keyword = node.get_token(Token.KEYWORD)
        # check if assign tokens needs to be split too
        line = [indent, *self.join_on_separator(node.get_tokens(Token.ASSIGN), separator), keyword]
        if not self.col_fit_in_line(line):
            head = [
                *self.split_to_multiple_lines(node.get_tokens(Token.ASSIGN), indent=indent, separator=cont_indent),
                indent,
                CONTINUATION,
                cont_indent,
                keyword,
            ]
            line = []
        else:
            head = []

        tokens, comments = self.split_tokens(
            node.tokens[node.tokens.index(keyword) + 1 :], line, self.split_on_every_arg, indent
        )
        head.extend(tokens)
        comment_tokens = []
        for comment in comments:
            comment_tokens.extend([indent, comment, EOL])

        node.tokens = comment_tokens + head
        return node

    def col_fit_in_line(self, tokens):
        return self.len_token_text(tokens) < self.line_length

    @staticmethod
    def len_token_text(tokens):
        return sum(len(token.value) for token in tokens)
