import re
import logging

log = logging.getLogger(__name__)

# TODO: this is not the best e.g. we capture numbers
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


_NOT_SET = "NOT_SET"


class CompletionContext(object):

    TYPE_TEST_CASE = "test_case"
    TYPE_INIT = "init"
    TYPE_RESOURCE = "resource"

    def __init__(self, doc, line=_NOT_SET, col=_NOT_SET):
        """
        :param robotframework_ls.workspace.Document doc:
        :param int line:
        :param int col:
        """
        self.doc = doc

        if col is _NOT_SET or line is _NOT_SET:
            assert col is _NOT_SET, (
                "Either line and col are not set, or both are set. Found: (%s, %s)"
                % (line, col)
            )
            assert line is _NOT_SET, (
                "Either line and col are not set, or both are set. Found: (%s, %s)"
                % (line, col)
            )

            # If both are not set, use the doc len as the selection.
            line, col = doc.get_last_line_col()

        self.sel = doc.selection(line, col)

    def get_type(self):
        path = self.doc.path
        if not path:
            return

        import os.path

        basename = os.path.basename(path)
        if basename.startswith("__init__"):
            return self.TYPE_INIT

        if basename.endswith(".resource"):
            return self.TYPE_RESOURCE

        return self.TYPE_TEST_CASE

    def get_accepted_section_header_words(self):
        sections = self.get_accepted_sections()
        ret = []
        for section in sections:
            for marker in section.markers:
                ret.append(marker.title())
        ret.sort()
        return ret

    def get_accepted_sections(self):
        from robotframework_ls.impl import robot_constants

        t = self.get_type()
        if t == self.TYPE_TEST_CASE:
            return robot_constants.TEST_CASE_FILE_SECTIONS

        elif t == self.TYPE_RESOURCE:
            return robot_constants.RESOURCE_FILE_SECTIONS

        elif t == self.TYPE_INIT:
            return robot_constants.INIT_FILE_SECTIONS

        else:
            log.critical("Unrecognized section: %s", t)
            return robot_constants.TEST_CASE_FILE_SECTIONS

    def get_ast(self):
        from robotframework_ls.impl import robot_constants
        from robot.parsing import get_model, get_resource_model, get_init_model

        source = self.doc.source

        t = self.get_type()
        if t == self.TYPE_TEST_CASE:
            return get_model(source)

        elif t == self.TYPE_RESOURCE:
            return get_resource_model(source)

        elif t == self.TYPE_INIT:
            return get_init_model(source)

        else:
            log.critical("Unrecognized section: %s", t)
            return robot_constants.TEST_CASE_FILE_SECTIONS

    def get_section_name(self):
        ast = self.get_ast()
        last_section_name = None
        for section in ast.sections:
            header = getattr(section, "header", None)
            if header is not None:
                # <= because the ast lineno is 1-based.
                if header.lineno <= self.sel.line:
                    header_name = header.value
                    last_section_name = header_name

                else:
                    return last_section_name

        return last_section_name

    def get_section(self, section_name):
        section_name = section_name.lower()
        accepted_sections = self.get_accepted_sections()

        for section in accepted_sections:
            for marker in section.markers:
                if marker.lower() == section_name:
                    return section
        return None
