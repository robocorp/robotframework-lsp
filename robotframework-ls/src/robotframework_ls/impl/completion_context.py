from robotframework_ls.impl.robot_workspace import RobotDocument
from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.robotframework_log import get_logger
import sys

log = get_logger(__name__)


_NOT_SET = "NOT_SET"

try:
    str_types = (str, unicode)
except NameError:
    str_types = (str,)


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
        :param robocorp_ls_core.workspace.Document doc:
        :param int line:
        :param int col:
        :param RobotWorkspace workspace:
        :param robocorp_ls_core.config.Config config:
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

    @instance_cache
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
    def get_current_variable(self, section=None):
        """
        :rtype: robotframework_ls.impl.ast_utils._TokenInfo|NoneType
        """
        from robotframework_ls.impl import ast_utils

        if section is None:
            section = self.get_ast_current_section()

        if section is None:
            return None
        return ast_utils.find_variable(section, self.sel.line, self.sel.col)

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

    def token_value_resolving_variables(self, token):
        from robotframework_ls.impl import ast_utils

        if isinstance(token, str_types):
            token = ast_utils.create_token(token)

        try:
            tokenized_vars = ast_utils.tokenize_variables(token)
        except:
            return token.value  # Unable to tokenize
        parts = []
        for v in tokenized_vars:
            if v.type == v.NAME:
                parts.append(str(v))

            elif v.type == v.VARIABLE:
                # Resolve variable from config
                initial_v = v = str(v)
                if v.startswith("${") and v.endswith("}"):
                    v = v[2:-1]
                    parts.append(self.convert_robot_variable(v, initial_v))
                else:
                    log.info("Cannot resolve variable: %s", v)
                    parts.append(v)  # Leave unresolved.

        joined_parts = "".join(parts)
        return joined_parts

    @instance_cache
    def get_resource_import_as_doc(self, resource_import):
        from robocorp_ls_core import uris
        import os.path
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

        ws = self._workspace

        for token in resource_import.tokens:
            if token.type == token.NAME:

                name_with_resolved_vars = self.token_value_resolving_variables(token)

                if not os.path.isabs(name_with_resolved_vars):
                    # It's a relative resource, resolve its location based on the
                    # current file.
                    check_paths = [
                        os.path.join(
                            os.path.dirname(self.doc.path), name_with_resolved_vars
                        )
                    ]
                    config = self.config
                    if config is not None:
                        for additional_pythonpath_entry in config.get_setting(
                            OPTION_ROBOT_PYTHONPATH, list, []
                        ):
                            check_paths.append(
                                os.path.join(
                                    additional_pythonpath_entry, name_with_resolved_vars
                                )
                            )

                else:
                    check_paths = [name_with_resolved_vars]

                for resource_path in check_paths:
                    doc_uri = uris.from_fs_path(resource_path)
                    resource_doc = ws.get_document(doc_uri, accept_from_file=True)
                    if resource_doc is None:
                        log.info("Resource not found: %s", resource_path)
                        continue
                    return resource_doc
        return None

    @instance_cache
    def get_resource_imports_as_docs(self):
        ret = []

        # Get keywords from resources
        resource_imports = self.get_resource_imports()
        for resource_import in resource_imports:
            resource_doc = self.get_resource_import_as_doc(resource_import)
            if resource_doc is not None:
                ret.append(resource_doc)

        return tuple(ret)

    def convert_robot_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

        if self.config is None:
            log.info(
                "Config not available while trying to convert variable: %s", var_name
            )
            value = value_if_not_found
        else:
            robot_variables = self.config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
            value = robot_variables.get(var_name)
            if value is None:
                log.info("Unable to find variable: %s", var_name)
                value = value_if_not_found
        value = str(value)
        return value
