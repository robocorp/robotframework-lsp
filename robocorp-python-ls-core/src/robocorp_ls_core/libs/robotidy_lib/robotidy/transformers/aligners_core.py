from collections import defaultdict
from typing import List, Tuple

from robot.api.parsing import ElseHeader, ElseIfHeader, ModelVisitor, Token
from robot.parsing.model import Statement

try:
    from robot.api.parsing import InlineIfHeader, TryHeader
except ImportError:
    InlineIfHeader, TryHeader = None, None

from robotidy.disablers import skip_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.skip import Skip
from robotidy.transformers import Transformer
from robotidy.utils import is_blank_multiline, round_to_four

WHITESPACE_TOKENS = frozenset({Token.SEPARATOR, Token.EOS})


class AlignKeywordsTestsSection(Transformer):

    ENABLED = False
    DEFAULT_WIDTH = 24
    HANDLES_SKIP = frozenset(
        {
            "skip_documentation",
            "skip_return_values",
            "skip_keyword_call",
            "skip_keyword_call_pattern",
            "skip_settings",
            "skip_arguments",
            "skip_setup",
            "skip_teardown",
            "skip_template",
            "skip_timeout",
            "skip_return",
            "skip_tags",
        }
    )

    def __init__(
        self,
        widths: str,
        alignment_type: str,
        handle_too_long: str,
        compact_overflow_limit: int = 2,
        skip: Skip = None,
    ):
        super().__init__(skip)
        self.is_inline = False
        self.indent = 1
        self.handle_too_long = self.parse_handle_too_long(handle_too_long)
        self.fixed_alignment = self.parse_alignment_type(alignment_type)
        self.compact_overflow_limit = compact_overflow_limit
        self.split_too_long = False
        # column widths map - 0: 40, 1: 30
        if widths:
            self.widths = self.parse_widths(widths)
        else:
            self.widths = None
        self.auto_widths = []

    @skip_if_disabled
    def visit_File(self, node):  # noqa
        self.split_too_long = self.is_split_too_long_enabled()
        return self.generic_visit(node)

    def parse_widths(self, widths):
        parsed_widths = dict()
        for index, width in enumerate(widths.split(",")):
            try:
                number = int(width)
                if number < 0:
                    raise ValueError("Should not be a negative number.")
            except ValueError:
                raise InvalidParameterValueError(
                    self.__class__.__name__,
                    "widths",
                    widths,
                    "Widths should be comma separated list of numbers equal or greater than 0.",
                ) from None
            parsed_widths[index] = number
        return parsed_widths

    def parse_handle_too_long(self, value):
        if value not in ("overflow", "compact_overflow", "ignore_line", "ignore_rest"):
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "handle_too_long",
                value,
                "Chose between modes: 'overflow' (align to the next column), 'compact_overflow' (), "
                "'ignore_line' (ignore this line in alignment) or 'ignore_rest' (align to long token and ignore rest)",
            )
        return value

    def parse_alignment_type(self, value):
        if value not in ("fixed", "auto"):
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "alignment_type",
                value,
                "Chose between two modes: 'fixed' (align to fixed width) or "
                "'auto' (align to longest token in column).",
            )
        return value == "fixed"

    def parse_documentation_mode(self, doc_mode):
        if doc_mode not in ("skip", "align_first_col"):
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "doc_mode",
                doc_mode,
                "Chose between two modes: 'skip' (default - do not align documentation) or "
                "'align_first_col' (align first indent in the documentation).",
            )
        return doc_mode == "skip"

    def visit_If(self, node):  # noqa
        # ignore inline ifs and their else/else if branches
        if self.is_inline:
            return node
        self.create_auto_widths_for_context(node)
        self.is_inline = InlineIfHeader and isinstance(node.header, InlineIfHeader)
        if self.is_inline:
            self.is_inline = False
            return node
        if not isinstance(node.header, (ElseHeader, ElseIfHeader)):
            self.indent += 1
        self.generic_visit(node)
        if not isinstance(node.header, (ElseHeader, ElseIfHeader)):
            self.indent -= 1
        self.remove_auto_widths_for_context()
        return node

    def visit_Try(self, node):  # noqa
        self.create_auto_widths_for_context(node)
        # do not increase header for Except, Else, Finally - it was done in Try already
        if isinstance(node.header, TryHeader):
            self.indent += 1
        self.generic_visit(node)
        if isinstance(node.header, TryHeader):
            self.indent -= 1
        self.remove_auto_widths_for_context()
        return node

    def visit_For(self, node):  # noqa
        self.create_auto_widths_for_context(node)
        self.indent += 1
        self.generic_visit(node)
        self.indent -= 1
        self.remove_auto_widths_for_context()
        return node

    visit_While = visit_For

    def get_width(self, col, override_default_zero=False):
        # If auto mode is enabled, use auto widths for current context (last defined widths)
        if self.auto_widths:
            widths = self.auto_widths[-1]
        else:
            widths = self.widths
        if not widths:
            return self.DEFAULT_WIDTH
        if col in widths:
            return widths[col]
        width = widths[len(widths) - 1]  # if there is no such column, use last column width
        if override_default_zero and width == 0:  # edge case where 0 is last of widths and we're overflowing
            return self.formatting_config.space_count
        return width

    def visit_SettingSection(self, node):  # noqa
        return node

    @skip_if_disabled
    def visit_Documentation(self, node):  # noqa
        if self.skip.documentation:
            return node
        # For every line:
        # {indent}...{aligned separator}{leave rest alone}
        width = self.get_width(0)
        for line in node.lines:
            first_sep = True
            prev_token = None
            for token in line:
                if token.type == Token.SEPARATOR:
                    if first_sep:
                        token.value = self.formatting_config.indent
                        first_sep = False
                        continue
                    if width == 0:
                        separator_len = round_to_four(len(prev_token.value) + self.formatting_config.space_count) - len(
                            prev_token.value
                        )
                    else:
                        separator_len = max(width - len(prev_token.value), self.formatting_config.space_count)
                    token.value = " " * separator_len
                    break
                elif token.type != Token.ARGUMENT:  # ...   # comment edge case
                    prev_token = token
        return node

    def create_auto_widths_for_context(self, node):
        if self.fixed_alignment:
            return
        counter = ColumnWidthCounter(
            self.disablers,
            self.skip.documentation,
            self.handle_too_long,
            self.widths,
            self.DEFAULT_WIDTH,
            self.formatting_config.space_count,
        )
        counter.visit(node)
        counter.calculate_column_widths()
        self.auto_widths.append(counter.widths)

    def remove_auto_widths_for_context(self):
        if not self.fixed_alignment:
            self.auto_widths.pop()

    def visit_ForHeader(self, node):  # noqa
        # Fix indent for FOR, IF, WHILE, TRY block headers & ends
        indent = Token(Token.SEPARATOR, (self.indent - 1) * self.formatting_config.indent)
        node.tokens = [indent] + list(node.tokens[1:])
        return node

    visit_End = visit_ForHeader  # TODO add other headers

    @skip_if_disabled
    def visit_KeywordCall(self, node):  # noqa
        if node.errors:
            return node
        if self.skip.keyword_call(node):
            return node
        return self.align_node(node, check_length=self.split_too_long, possible_assign=True)

    def should_skip_return_values(self, line, possible_assign):
        return possible_assign and self.skip.return_values and any(token.type == Token.ASSIGN for token in line)

    def align_node(self, node, check_length: bool, possible_assign: bool = False):
        indent = Token(Token.SEPARATOR, self.indent * self.formatting_config.indent)
        aligned_lines = []
        for line in node.lines:
            assign, tokens, skip_width = self.split_assign(line, possible_assign)
            aligned_line = self.align_line(tokens, skip_width)
            if aligned_line is None:
                aligned_lines.extend(line)
                continue
            aligned_line = [indent] + assign + aligned_line
            if check_length and self.is_line_too_long(aligned_line):
                split_node = self.split_too_long_node(node)
                return self.align_node(split_node, check_length=False)
            aligned_lines.extend(aligned_line)
        return Statement.from_tokens(aligned_lines)

    def split_assign(self, line: List, possible_assign: bool) -> Tuple[List, List, int]:
        """
        This method returns return values together with their separators in case
        we don't want to align them.

        Returns:
            A tuple, containing:
            - return values,
            - remaining tokens,
            - widths of the return values (used to determine next alignment column)
        """
        if not self.should_skip_return_values(line, possible_assign):
            return [], get_data_tokens(line), 0
        assign = []
        assign_found = False
        for index, token in enumerate(line[1:], start=1):
            if token.type == Token.ASSIGN:
                assign_found = True
            elif assign_found and token.type not in (Token.SEPARATOR, Token.ASSIGN):
                skip_width = sum(len(token.value) for token in assign[:-1])
                return (
                    assign[:-1],
                    get_data_tokens(line[index:]),
                    skip_width,
                )
            assign.append(token)

    @skip_if_disabled
    def visit_Tags(self, node):  # noqa
        if node.errors or self.skip.setting("Tags"):
            return node
        return self.align_node(node, check_length=False)

    @skip_if_disabled
    def visit_Return(self, node):  # noqa
        if node.errors or self.skip.setting("Return_Statement"):
            return node
        return self.align_node(node, check_length=False)

    visit_ReturnStatement = visit_Return

    @skip_if_disabled
    def visit_Template(self, node):  # noqa
        if node.errors or self.skip.setting("Template"):
            return node
        return self.align_node(node, check_length=False)

    @skip_if_disabled
    def visit_Timeout(self, node):  # noqa
        if node.errors or self.skip.setting("Timeout"):
            return node
        return self.align_node(node, check_length=False)

    @skip_if_disabled
    def visit_Teardown(self, node):  # noqa
        if node.errors or self.skip.setting("Teardown"):
            return node
        return self.align_node(node, check_length=False)

    @skip_if_disabled
    def visit_Setup(self, node):  # noqa
        if node.errors or self.skip.setting("Setup"):
            return node
        return self.align_node(node, check_length=False)

    @skip_if_disabled
    def visit_Arguments(self, node):  # noqa
        if node.errors or self.skip.setting("Arguments"):
            return node
        return self.align_node(node, check_length=False)

    def align_line(self, line: List, skip_width: int):
        """
        Align single line of the node.

        New, aligned line consist of the indent and tokens separated by separator. The separator width is calculated
        depending on the configured particular column width and the alignment mode.

        The alignment mode could be auto or fixed - it's calculated before running this method and self.widths already
        returns width of the column according to the selected mode.

        First, empty multiline is return as it can't be aligned.
        Then comments are removed from the line - they will be added at the end of the alignment.
        Afterwards we start to align the tokens.
        If the configured width is set to 0 it means we don't need to calculate width of the separator - we should use
        length of the token with minimal separator rounded to the closest multiply of 4.
        Otherwise, we are calculating if line will fit in width of the column. In case it will not fit there are
        several options (configurable via ``handle_too_long):
            - ignore_line - the whole line will be separated using fixed, minimal width of the separator
            - ignore_rest - all tokens before too long token will be aligned to the columns, but remaining tokens will
              be aligned using fixed, minimal width of the separator
            - compact_overflow - the too long token will go over the width of the column, but it will try to fit it
              together with next token (in second column)
            - overflow - we are looking for next column width that will fit our token

        At the end comments are appended at the end of the line and line is returned.
        """
        if is_blank_multiline(line):  # ...\n edge case
            line[-1].value = line[-1].value.lstrip(" \t")  # normalize eol from '  \n' to '\n'
            return line
        tokens, comments = separate_comments(line)
        if len(tokens) < 2:  # only happens with weird encoding, better to skip
            return None
        # skip_tokens, tokens = self.skip_return_values_if_needed(tokens)
        aligned = self.align_tokens(tokens[:-2], skip_width)
        last_token = strip_extra_whitespace(tokens[-2])
        aligned.extend([last_token, *join_comments(comments), tokens[-1]])
        return aligned

    def too_many_misaligned_cols(self, misaligned_cols: int, prev_overflow_len: int, tokens: List, index: int):
        return misaligned_cols >= self.compact_overflow_limit and prev_overflow_len and index < len(tokens) - 1

    def find_starting_column(self, skip_width: int):
        """
        If we're skipping values at the beginning of the line,
        we need to find next column for remaining tokens.
        """
        column = 0
        while skip_width > 0:
            width = self.get_width(column, override_default_zero=True)
            skip_width -= width
            column += 1
        return column, abs(skip_width)

    def get_start_column_and_aligned(self, skip_width: int, min_separator: int):
        """
        In case we are skipping return tokens alignment, calculate starting column and create leading separator.
        """
        if skip_width == 0:
            return 0, 0, []
        column, skip_width = self.find_starting_column(skip_width)
        if skip_width < min_separator:
            prev_overflow_len = min_separator - skip_width
            skip_width = min_separator
        else:
            prev_overflow_len = 0
        return column, prev_overflow_len, [get_separator(skip_width)]

    def align_tokens(self, tokens: List, skip_width: int):
        last_assign, misaligned_cols = 0, 0
        min_separator = self.formatting_config.space_count
        column, prev_overflow_len, aligned = self.get_start_column_and_aligned(skip_width, min_separator)
        for index, token in enumerate(tokens):
            aligned.append(token)
            width = self.get_width(column)
            if width == 0:
                separator_len = round_to_four(len(token.value) + min_separator) - len(token.value)
            else:
                separator_len = width - len(token.value) - prev_overflow_len
                if separator_len >= min_separator:
                    prev_overflow_len = 0
                    misaligned_cols = 0
                else:
                    if self.handle_too_long == "ignore_line":
                        return align_fixed(tokens, min_separator)
                    if self.handle_too_long == "ignore_rest":
                        return aligned + align_fixed(tokens[index + 1 :], min_separator, start_sep=True)
                    if self.handle_too_long == "compact_overflow":
                        required_width = len(token.value) + min_separator + prev_overflow_len
                        separator_len = min_separator
                        prev_overflow_len = required_width - width
                        misaligned_cols += 1
                        while prev_overflow_len > width:
                            column += 1
                            width = self.get_width(column, override_default_zero=True)
                            prev_overflow_len -= width
                            misaligned_cols += 1
                        if self.too_many_misaligned_cols(misaligned_cols, prev_overflow_len, tokens, index):
                            # check if next col fits next token with prev_overflow, if not, jump to the next column
                            next_token = tokens[index + 1]
                            next_width = self.get_width(column + 1, override_default_zero=True)
                            required_width = next_width - prev_overflow_len - len(next_token.value)
                            if required_width < min_separator:
                                column += 1
                                separator_len = next_width - prev_overflow_len + min_separator
                                prev_overflow_len = 0
                    else:  # "overflow"
                        while round_to_four(len(token.value) + min_separator) > width:
                            column += 1
                            width += self.get_width(column, override_default_zero=True)
                        separator_len = width - len(token.value)
            separator_len = max(
                min_separator, separator_len
            )  # extra precautious: separator should never be less than min_sep
            aligned.append(get_separator(separator_len))
            column += 1 + (separator_len == width)
        return aligned

    def is_line_too_long(self, line):
        if "SplitTooLongLine" not in self.transformers:
            return False
        if not self.transformers["SplitTooLongLine"].split_on_every_arg:  # TODO not support for overflow yet
            return False
        line_length = get_line_length(line)
        return line_length > self.transformers["SplitTooLongLine"].line_length

    def is_split_too_long_enabled(self):
        return "SplitTooLongLine" in self.transformers

    def split_too_long_node(self, node):
        return self.transformers["SplitTooLongLine"].split_keyword_call(node)


def strip_extra_whitespace(token):
    if not token.value:
        return token
    token.value = token.value.strip()
    return token


def separate_comments(tokens):
    non_comments, comments = [], []
    for token in tokens:
        if token.type == Token.COMMENT:
            comments.append(token)
        else:
            non_comments.append(token)
    return non_comments, comments


def join_comments(comments):
    tokens = []
    separator = get_separator(2)
    for token in comments:
        tokens.append(separator)
        tokens.append(token)
    return tokens


def align_fixed(tokens, sep_len, start_sep=False):
    """Align tokens with fixed spacing."""
    sep_token = get_separator(sep_len)
    aligned = [sep_token] if start_sep else []
    for token in tokens:
        aligned.append(token)
        aligned.append(sep_token)
    return aligned


def get_line_length(tokens):
    return sum(len(token.value) for token in tokens)


def get_data_tokens(tokens):
    return [token for token in tokens if token.type not in WHITESPACE_TOKENS]


def get_separator(sep_len: int) -> Token:
    return Token(Token.SEPARATOR, sep_len * " ")


class ColumnWidthCounter(ModelVisitor):
    NON_DATA_TOKENS = frozenset((Token.SEPARATOR, Token.COMMENT, Token.EOL, Token.EOS))

    def __init__(self, disablers, skip_documentation, handle_too_long, max_widths, default_width, min_separator):
        self.skip_documentation = skip_documentation
        self.handle_too_long = handle_too_long
        self.max_widths = max_widths
        self.default_width = default_width
        self.min_separator = min_separator
        self.raw_widths = defaultdict(list)
        self.widths = dict()
        self.disablers = disablers

    def get_width(self, col):
        if not self.max_widths:
            return self.default_width
        if col in self.max_widths:
            return self.max_widths[col]
        return self.max_widths[len(self.max_widths) - 1]  # if there is no such column, use last column width

    def calculate_column_widths(self):
        if self.max_widths:
            self.widths.update(self.max_widths)
        for column, widths in self.raw_widths.items():
            max_width = self.get_width(column)
            if max_width == 0:
                self.widths[column] = max(widths)
            else:
                filter_widths = [width for width in widths if width <= max_width]
                self.widths[column] = max(filter_widths, default=max_width)

    @skip_if_disabled
    def visit_KeywordCall(self, node):  # noqa
        if node.errors:
            return node
        for line in node.lines:
            # if assign disabled and assign in line: continue
            data_tokens = [token for token in line if token.type not in self.NON_DATA_TOKENS]
            raw_lens = {}
            for column, token in enumerate(data_tokens):
                max_width = self.get_width(column)
                token_len = round_to_four(len(token.value) + self.min_separator)
                if max_width == 0 or token_len <= max_width:
                    raw_lens[column] = token_len
                elif self.handle_too_long == "ignore_line":
                    raw_lens = {}
                    break
                else:  # ignore_rest, overflow and compact_overflow
                    break
            for col, token in raw_lens.items():
                self.raw_widths[col].append(token)

    visit_Arguments = (
        visit_Setup
    ) = visit_Teardown = visit_Timeout = visit_Template = visit_Return = visit_Tags = visit_KeywordCall  # TODO skip

    @skip_if_disabled
    def visit_Documentation(self, node):  # noqa
        if self.skip_documentation:
            return
        doc_header_len = round_to_four(len(node.data_tokens[0].value) + self.min_separator)
        self.raw_widths[0].append(doc_header_len)
