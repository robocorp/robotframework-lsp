from robot.api.parsing import ModelTransformer, Token

try:
    from robot.api.parsing import InlineIfHeader
except ImportError:
    InlineIfHeader = None
from robotidy.decorators import check_start_end_line
from robotidy.utils import ROBOT_VERSION


EOL = Token(Token.EOL)
CONTINUATION = Token(Token.CONTINUATION)


class SplitTooLongLine(ModelTransformer):
    """
    Split too long lines.
    If any line in keyword call exceeds given length limit (120 by default) it will be
    split:

        Keyword With Longer Name    ${arg1}    ${arg2}    ${arg3}  # let's assume that arg2 is at 120 char

    To:

        # let's assume that arg2 is at 120 char
        Keyword With Longer Name
        ...    ${arg1}
        ...    ${arg2}
        ...    ${arg3}

    Allowed line length is configurable using global parameter ``--line-length``:

        robotidy --line-length 140 src.robot

    Or using dedicated for this transformer parameter ``line_length``:

        robotidy --configure SplitTooLongLine:line_length:140 src.robot

    Using ``split_on_every_arg`` flag (``True`` by default), you can force the formatter to fill arguments in one line
    until character limit:

        Keyword With Longer Name    ${arg1}
        ...    ${arg2}    ${arg3}

    Supports global formatting params: ``spacecount``, ``separator``, ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/SplitTooLongLine.html for more examples.
    """

    def __init__(self, line_length: int = None, split_on_every_arg: bool = True):
        super().__init__()
        self._line_length = line_length
        self.split_on_every_arg = split_on_every_arg

    @property
    def line_length(self):
        return self.formatting_config.line_length if self._line_length is None else self._line_length

    def visit_If(self, node):  # noqa
        if self.is_inline(node):
            return node
        if node.orelse:
            self.generic_visit(node.orelse)
        return self.generic_visit(node)

    @staticmethod
    def is_inline(node):
        return ROBOT_VERSION.major > 4 and isinstance(node.header, InlineIfHeader)

    @check_start_end_line
    def visit_KeywordCall(self, node):  # noqa
        if all(line[-1].end_col_offset < self.line_length for line in node.lines):
            return node
        return self.split_keyword_call(node)

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

    def split_keyword_call(self, node):
        separator = Token(Token.SEPARATOR, self.formatting_config.separator)
        indent = node.tokens[0]

        split_every_arg = self.split_on_every_arg
        keyword = node.get_token(Token.KEYWORD)
        line = [indent, *self.join_on_separator(node.get_tokens(Token.ASSIGN), separator), keyword]
        if not self.col_fit_in_line(line):
            split_every_arg
            head = [
                *self.split_to_multiple_lines(node.get_tokens(Token.ASSIGN), indent=indent, separator=separator),
                indent,
                CONTINUATION,
                separator,
                keyword,
            ]
            line = []
        else:
            head = []

        comments = []

        # Comments with separators inside them are split into
        # [COMMENT, SEPARATOR, COMMENT] tokens in the AST, so in order to preserve the
        # original comment, we need a lookback on the separator tokens.
        last_separator = None

        rest = node.tokens[node.tokens.index(keyword) + 1 :]
        for token in rest:
            if token.type == Token.SEPARATOR:
                last_separator = token
            elif token.type in {Token.EOL, Token.CONTINUATION}:
                continue
            elif token.type == Token.COMMENT:
                # AST splits comments with separators, e.g.
                #
                # "# Comment     rest" -> ["# Comment", "     ", "rest"].
                #
                # Notice the third value not starting with a hash - that's what this
                # condition is about:
                if not str(token).startswith("#"):
                    # -2 because -1 is the EOL
                    comments[-2].value += last_separator.value + token.value
                else:
                    comments += [indent, token, EOL]
            elif token.type == Token.ARGUMENT:
                if token.value == "":
                    token.value = "${EMPTY}"
                if self.split_on_every_arg or not self.col_fit_in_line(line + [separator, token]):
                    line.append(EOL)
                    head += line
                    line = [indent, CONTINUATION, separator, token]
                else:
                    line += [separator, token]

        # last line
        line.append(EOL)
        head += line

        node.tokens = comments + head
        return node

    def col_fit_in_line(self, tokens):
        return self.len_token_text(tokens) < self.line_length

    @staticmethod
    def len_token_text(tokens):
        return sum(len(token.value) for token in tokens)
