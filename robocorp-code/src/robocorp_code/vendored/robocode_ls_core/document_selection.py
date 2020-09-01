# TODO: this is not the best e.g. we capture numbers
import re

RE_START_WORD = re.compile("[A-Za-z_0-9]*$")
RE_END_WORD = re.compile("^[A-Za-z_0-9]*")


class DocumentSelection(object):
    def __init__(self, doc, line, col):
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
    def current_line(self):
        return self.doc.get_line(self.line)

    @property
    def line_to_column(self):
        current_line = self.current_line
        if not current_line:
            return ""
        line_start = current_line[: self.col]

        return line_start

    @property
    def word_at_position(self):
        """Get the word under the cursor returning the start and end positions."""
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
    def word_to_cursor(self):
        """Get the word under the cursor returning the start and end positions."""
        current_line = self.current_line
        if not current_line:
            return ""

        col = self.col
        # Split word in two
        start = current_line[:col]

        # Take end of start and start of end to find word
        # These are guaranteed to match, even if they match the empty string
        m_start = RE_START_WORD.findall(start)

        return m_start[0]
