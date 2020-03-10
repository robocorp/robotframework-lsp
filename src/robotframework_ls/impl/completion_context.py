import re
import logging
from robotframework_ls.impl.robot_workspace import RobotDocument
from robotframework_ls.cache import instance_cache

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

    TYPE_TEST_CASE = RobotDocument.TYPE_TEST_CASE
    TYPE_INIT = RobotDocument.TYPE_INIT
    TYPE_RESOURCE = RobotDocument.TYPE_RESOURCE

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

    @instance_cache
    def get_type(self):
        return self.doc.get_type()

    @instance_cache
    def get_ast(self):
        return self.doc.get_ast()

    @instance_cache
    def get_ast_current_section(self):
        """
        :rtype: robot.parsing.model.blocks.Section|NoneType
        """
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        section = ast_utils.find_section(ast, self.sel.line)
        return section

    def get_accepted_section_header_words(self):
        """
        :rtype: list(str)
        """
        sections = self._get_accepted_sections()
        ret = []
        for section in sections:
            for marker in section.markers:
                ret.append(marker.title())
        ret.sort()
        return ret

    def get_current_section_name(self):
        """
        :rtype: str|NoneType
        """
        section = self.get_ast_current_section()

        section_name = None
        header = getattr(section, "header", None)
        if header is not None:
            section_name = header.value

        return section_name

    def _get_accepted_sections(self):
        """
        :rtype: list(robot_constants.Section)
        """
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

    def get_section(self, section_name):
        """
        :rtype: robot_constants.Section
        """
        section_name = section_name.lower()
        accepted_sections = self._get_accepted_sections()

        for section in accepted_sections:
            for marker in section.markers:
                if marker.lower() == section_name:
                    return section
        return None

    def get_current_token(self):
        """
        :rtype: robotframework_ls.impl.ast_utils._TokenInfo|NoneType
        """
        from robotframework_ls.impl import ast_utils

        section = self.get_ast_current_section()
        if section is None:
            return None
        return ast_utils.find_token(section, self.sel.line, self.sel.col)

    @instance_cache
    def get_imported_libraries(self):
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for library_import in ast_utils.iter_library_imports(ast):
            ret.append(library_import.node)
        return ret
