# TODO: this is not the best e.g. we capture numbers
import re

from robocorp_ls_core.protocols import IDocumentSelection, IDocument


RE_START_WORD = re.compile(r"[\w]*$")
RE_END_WORD = re.compile(r"^[\w]*")


def word_to_column(line_to_cursor):
    m_start = RE_START_WORD.findall(line_to_cursor)

    return m_start[0]


class DocumentSelection(object):
    def __init__(self, doc: IDocument, line: int, col: int):
        if line < 0:
            line = 0

        if col < 0:
            col = 0

        self.doc = doc
        self.line = line
        self.col = col

    @property
    def offset_at_position(self):
        """Return the byte-offset pointed at by the given position."""
        offset = 0
        for i, curr_line in enumerate(self.doc.iter_lines()):
            if i == self.line:
                break
            offset += len(curr_line)

        return offset + self.col

    @property
    def current_line(self) -> str:
        return self.doc.get_line(self.line)

    @property
    def line_to_column(self) -> str:
        current_line = self.current_line
        if not current_line:
            return ""
        line_start = current_line[: self.col]

        return line_start

    @property
    def line_to_end(self) -> str:
        current_line = self.current_line
        if not current_line:
            return ""
        return current_line[self.col :]

    @property
    def word_at_column(self) -> str:
        current_line = self.current_line
        if not current_line:
            return ""

        col = self.col
        # Split word in two
        start = current_line[:col]
        end = current_line[col:]

        # Take end of start and start of end to find word
        # These are guaranteed to match, even if they match the empty string
        m_start = RE_START_WORD.findall(start)
        m_end = RE_END_WORD.findall(end)

        return m_start[0] + m_end[-1]

    @property
    def word_to_column(self) -> str:
        line_to_cursor = self.line_to_column
        return word_to_column(line_to_cursor)

    @property
    def word_from_column(self) -> str:
        current_line = self.current_line
        if not current_line:
            return ""

        col = self.col
        # Split word in two
        end = current_line[col:]

        m_end = RE_END_WORD.findall(end)

        return m_end[-1]

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IDocumentSelection = check_implements(self)
