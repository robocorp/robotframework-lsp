import re
from robotframework_ls.impl.robot_workspace import RobotDocument
from robotframework_ls.cache import instance_cache
from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)

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


class _Memo(object):
    def __init__(self):
        self._followed_imports_variables = {}
        self._followed_imports = {}
        self._completed_libraries = {}

    def follow_import(self, uri):
        if uri not in self._followed_imports:
            self._followed_imports[uri] = True
            return True

        return False

    def follow_import_variables(self, uri):
        if uri not in self._followed_imports_variables:
            self._followed_imports_variables[uri] = True
            return True

        return False

    def complete_for_library(self, library_name):
        if library_name not in self._completed_libraries:
            self._completed_libraries[library_name] = True
            return True

        return False


class CompletionContext(object):

    TYPE_TEST_CASE = RobotDocument.TYPE_TEST_CASE
    TYPE_INIT = RobotDocument.TYPE_INIT
    TYPE_RESOURCE = RobotDocument.TYPE_RESOURCE

    def __init__(
        self, doc, line=_NOT_SET, col=_NOT_SET, workspace=None, config=None, memo=None
    ):
        """
        :param robotframework_ls.workspace.Document doc:
        :param int line:
        :param int col:
        :param RobotWorkspace workspace:
        :param robotframework_ls.config.config.Config config:
        :param _Memo memo:
        """

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

        memo = _Memo() if memo is None else memo

        sel = doc.selection(line, col)

        self._doc = doc
        self._sel = sel
        self._workspace = workspace
        self._config = config
        self._memo = memo
        self._original_ctx = None

    def create_copy(self, doc):
        ctx = CompletionContext(
            doc,
            line=0,
            col=0,
            workspace=self._workspace,
            config=self._config,
            memo=self._memo,
        )
        ctx._original_ctx = self
        return ctx

    @property
    def original_doc(self):
        if self._original_ctx is None:
            return self._doc
        return self._original_ctx.original_doc

    @property
    def original_sel(self):
        if self._original_ctx is None:
            return self._sel
        return self._original_ctx.original_sel

    @property
    def doc(self):
        return self._doc

    @property
    def sel(self):
        return self._sel

    @property
    def memo(self):
        return self._memo

    @property
    def config(self):
        return self._config

    @property
    def workspace(self):
        return self._workspace

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
            try:
                section_name = header.name
            except AttributeError:
                section_name = header.value  # older version of 3.2

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
        return tuple(ret)

    @instance_cache
    def get_resource_imports(self):
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for resource in ast_utils.iter_resource_imports(ast):
            ret.append(resource.node)
        return tuple(ret)

    @instance_cache
    def iter_imports_docs(self):
        from robotframework_ls import uris
        import os.path

        ws = self._workspace

        # Get keywords from resources
        resource_imports = self.get_resource_imports()
        for resource_import in resource_imports:
            for token in resource_import.tokens:
                if token.type == token.NAME:
                    parts = []
                    for v in token.tokenize_variables():
                        if v.type == v.NAME:
                            parts.append(str(v))

                        elif v.type == v.VARIABLE:
                            # Resolve variable from config
                            v = str(v)
                            if v.startswith("${") and v.endswith("}"):
                                v = v[2:-1]
                                parts.append(self.convert_robot_variable(v))
                            else:
                                log.info("Cannot resolve variable: %s", v)

                    resource_path = "".join(parts)
                    if not os.path.isabs(resource_path):
                        # It's a relative resource, resolve its location based on the
                        # current file.
                        resource_path = os.path.join(
                            os.path.dirname(self.doc.path), resource_path
                        )

                    if not os.path.exists(resource_path):
                        log.info("Resource not found: %s", resource_path)
                        continue

                    doc_uri = uris.from_fs_path(resource_path)
                    resource_doc = ws.get_document(doc_uri, create=False)
                    if resource_doc is None:
                        resource_doc = ws.create_untracked_document(doc_uri)

                    yield resource_doc

    def convert_robot_variable(self, var_name):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

        robot_variables = self.config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        value = robot_variables.get(var_name)
        if value is None:
            log.info("Unable to find variable: %s", var_name)
            value = ""
        return str(value)
