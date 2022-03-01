import sys
from typing import Optional, Any, List, Tuple, Set, Callable, Dict, Union

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.lsp import CompletionItemTypedDict, MarkupContentTypedDict
from robocorp_ls_core.protocols import IMonitor, Sentinel, IConfig, IDocumentSelection
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    IRobotDocument,
    ICompletionContext,
    TokenInfo,
    IRobotWorkspace,
    IKeywordDefinition,
    ILibraryImportNode,
    KeywordUsageInfo,
    CompletionType,
    IResourceImportNode,
    ICompletionContextDependencyGraph,
    IRobotToken,
)
from robotframework_ls.impl.robot_workspace import RobotDocument


log = get_logger(__name__)


class _Memo(object):
    pass


class BaseContext(object):
    def __init__(self, workspace: IRobotWorkspace, config: IConfig, monitor: IMonitor):
        self._workspace = workspace
        self._config = config
        self._monitor = monitor

    @property
    def monitor(self) -> IMonitor:
        return self._monitor

    @property
    def workspace(self) -> IRobotWorkspace:
        return self._workspace

    @property
    def config(self) -> IConfig:
        return self._config

    def check_cancelled(self) -> None:
        self._monitor.check_cancelled()

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements
        from robotframework_ls.impl.protocols import IBaseCompletionContext

        _: IBaseCompletionContext = check_implements(self)


class CompletionContext(object):

    TYPE_TEST_CASE = RobotDocument.TYPE_TEST_CASE
    TYPE_INIT = RobotDocument.TYPE_INIT
    TYPE_RESOURCE = RobotDocument.TYPE_RESOURCE

    def __init__(
        self,
        doc,
        line=Sentinel.SENTINEL,
        col=Sentinel.SENTINEL,
        workspace=None,
        config=None,
        memo=None,
        monitor: Optional[IMonitor] = NULL,
    ) -> None:
        """
        :param robocorp_ls_core.workspace.Document doc:
        :param int line:
        :param int col:
        :param RobotWorkspace workspace:
        :param robocorp_ls_core.config.Config config:
        :param _Memo memo:
        """

        if col is Sentinel.SENTINEL or line is Sentinel.SENTINEL:
            assert (
                col is Sentinel.SENTINEL
            ), "Either line and col are not set, or both are set. Found: (%s, %s)" % (
                line,
                col,
            )
            assert (
                line is Sentinel.SENTINEL
            ), "Either line and col are not set, or both are set. Found: (%s, %s)" % (
                line,
                col,
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
        self._original_ctx: Optional[CompletionContext] = None
        self._monitor = monitor or NULL
        self.type = CompletionType.regular

        self._id_to_compute_documentation: Dict[
            int, Callable[[], MarkupContentTypedDict]
        ] = {}

    def assign_documentation_resolve(
        self,
        completion_item: CompletionItemTypedDict,
        compute_documentation: Callable[[], MarkupContentTypedDict],
    ) -> None:
        if self._original_ctx is not None:
            self._original_ctx.assign_documentation_resolve(
                completion_item, compute_documentation
            )
        else:
            next_id = len(self._id_to_compute_documentation)
            self._id_to_compute_documentation[next_id] = compute_documentation
            completion_item["data"] = {"id": next_id, "ctx": id(self)}

    def resolve_completion_item(
        self, data, completion_item: CompletionItemTypedDict, monaco=False
    ) -> None:
        if self._original_ctx is not None:
            self._original_ctx.resolve_completion_item(data, completion_item)
        else:
            compute_documentation = self._id_to_compute_documentation.get(
                data.get("id")
            )
            if compute_documentation is not None:
                marked: Optional[MarkupContentTypedDict] = compute_documentation()
                if marked:
                    if monaco:
                        if marked["kind"] == "markdown":
                            completion_item["documentation"] = {
                                "value": marked["value"]
                            }
                        else:
                            completion_item["documentation"] = marked["value"]
                    else:
                        completion_item["documentation"] = marked

    @property
    def monitor(self) -> IMonitor:
        return self._monitor

    def check_cancelled(self) -> None:
        self._monitor.check_cancelled()

    def create_copy_with_selection(self, line: int, col: int) -> ICompletionContext:
        doc = self._doc
        ctx = CompletionContext(
            doc,
            line=line,
            col=col,
            workspace=self._workspace,
            config=self._config,
            memo=self._memo,
            monitor=self._monitor,
        )
        ctx._original_ctx = self
        return ctx

    def create_copy(self, doc: IRobotDocument) -> ICompletionContext:
        ctx = CompletionContext(
            doc,
            line=0,
            col=0,
            workspace=self._workspace,
            config=self._config,
            memo=self._memo,
            monitor=self._monitor,
        )
        ctx._original_ctx = self
        return ctx

    @property
    def original_doc(self) -> IRobotDocument:
        if self._original_ctx is None:
            return self._doc
        return self._original_ctx.original_doc

    @property
    def original_sel(self) -> IDocumentSelection:
        if self._original_ctx is None:
            return self._sel
        return self._original_ctx.original_sel

    @property
    def doc(self) -> IRobotDocument:
        return self._doc

    @property
    def sel(self) -> IDocumentSelection:
        return self._sel

    @property
    def memo(self) -> Any:
        return self._memo

    @property
    def config(self) -> Optional[IConfig]:
        return self._config

    @property
    def workspace(self) -> IRobotWorkspace:
        return self._workspace

    @instance_cache
    def get_type(self) -> Any:
        return self.doc.get_type()

    @instance_cache
    def get_ast(self) -> Any:
        return self.doc.get_ast()

    @instance_cache
    def get_ast_current_section(self) -> Any:
        """
        :rtype: robot.parsing.model.blocks.Section|NoneType
        """
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        section = ast_utils.find_section(ast, self.sel.line)
        return section

    def get_accepted_section_header_words(self) -> List[str]:
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

    def get_current_section_name(self) -> Optional[str]:
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

    def _get_accepted_sections(self) -> list:
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

    def get_section(self, section_name: str) -> Any:
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
    def get_current_token(self) -> Optional[TokenInfo]:
        from robotframework_ls.impl import ast_utils

        section = self.get_ast_current_section()
        if section is None:
            return None
        return ast_utils.find_token(section, self.sel.line, self.sel.col)

    def get_all_variables(self):
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        return tuple(ast_utils.iter_variables(ast))

    @instance_cache
    def get_current_variable(self, section=None) -> Optional[TokenInfo]:
        from robotframework_ls.impl import ast_utils

        if section is None:
            section = self.get_ast_current_section()

        if section is None:
            return None
        return ast_utils.find_variable(section, self.sel.line, self.sel.col)

    @instance_cache
    def get_imported_libraries(self) -> Tuple[ILibraryImportNode, ...]:
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for library_import in ast_utils.iter_library_imports(ast):
            if library_import.node.name:
                ret.append(library_import.node)
        return tuple(ret)

    @instance_cache
    def get_resource_imports(self):
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for resource in ast_utils.iter_resource_imports(ast):
            if resource.node.name:
                ret.append(resource.node)
        return tuple(ret)

    @instance_cache
    def get_variable_imports(self):
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for resource in ast_utils.iter_variable_imports(ast):
            if resource.node.name:
                ret.append(resource.node)
        return tuple(ret)

    def token_value_resolving_variables(self, token: Union[str, IRobotToken]):
        from robotframework_ls.impl import ast_utils

        robot_token: IRobotToken
        if isinstance(token, str):
            robot_token = ast_utils.create_token(token)
        else:
            robot_token = token

        try:
            tokenized_vars = ast_utils.tokenize_variables(robot_token)
        except:
            return robot_token.value  # Unable to tokenize
        parts = []
        for v in tokenized_vars:
            if v.type == v.NAME:
                parts.append(str(v))

            elif v.type == v.VARIABLE:
                # Resolve variable from config
                initial_v = v = str(v)
                if v.startswith("${") and v.endswith("}"):
                    v = v[2:-1]
                    parts.append(self._convert_robot_variable(v, initial_v))
                elif v.startswith("%{") and v.endswith("}"):
                    v = v[2:-1]
                    parts.append(self._convert_environment_variable(v, initial_v))
                else:
                    log.info("Cannot resolve variable: %s", v)
                    parts.append(v)  # Leave unresolved.

        joined_parts = "".join(parts)
        return joined_parts

    @instance_cache
    def get_resource_import_as_doc(self, resource_import) -> Optional[IRobotDocument]:
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
                        os.path.normpath(
                            os.path.join(
                                os.path.dirname(self.doc.path), name_with_resolved_vars
                            )
                        )
                    ]
                    config = self.config
                    if config is not None:
                        for additional_pythonpath_entry in config.get_setting(
                            OPTION_ROBOT_PYTHONPATH, list, []
                        ):
                            check_paths.append(
                                os.path.normpath(
                                    os.path.join(
                                        additional_pythonpath_entry,
                                        name_with_resolved_vars,
                                    )
                                )
                            )

                    for path in sys.path:
                        check_paths.append(
                            os.path.normpath(
                                os.path.join(
                                    path,
                                    name_with_resolved_vars,
                                )
                            )
                        )

                    # Make the entries in the list unique (keeping order).
                    seen: Set[str] = set()
                    add_it_and_return_none = seen.add
                    check_paths = [
                        x
                        for x in check_paths
                        if x not in seen and not add_it_and_return_none(x)
                    ]

                else:
                    check_paths = [name_with_resolved_vars]

                for resource_path in check_paths:
                    doc_uri = uris.from_fs_path(resource_path)
                    resource_doc = ws.get_document(doc_uri, accept_from_file=True)
                    if resource_doc is None:
                        continue
                    return resource_doc

                log.info(
                    "Unable to find: %s (checked paths: %s)",
                    name_with_resolved_vars,
                    check_paths,
                )

        return None

    def get_variable_import_as_doc(self, variables_import) -> Optional[IRobotDocument]:
        return self.get_resource_import_as_doc(variables_import)

    @instance_cache
    def get_resource_imports_as_docs(
        self,
    ) -> Tuple[Tuple[IResourceImportNode, Optional[IRobotDocument]], ...]:
        ret: List[Tuple[IResourceImportNode, Optional[IRobotDocument]]] = []

        # Get keywords from resources
        resource_imports = self.get_resource_imports()
        for resource_import in resource_imports:
            resource_doc = self.get_resource_import_as_doc(resource_import)
            ret.append((resource_import, resource_doc))

        return tuple(ret)

    @instance_cache
    def get_variable_imports_as_docs(self) -> Tuple[IRobotDocument, ...]:
        ret: List[IRobotDocument] = []

        variable_imports = self.get_variable_imports()
        for variable_import in variable_imports:
            variable_doc = self.get_variable_import_as_doc(variable_import)
            if variable_doc is not None:
                ret.append(variable_doc)

        return tuple(ret)

    def _resolve_builtin(self, var_name, value_if_not_found, log_info):
        from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES_RESOLVED

        ret = BUILTIN_VARIABLES_RESOLVED.get(var_name, Sentinel.SENTINEL)
        if ret is Sentinel.SENTINEL:
            if var_name == "CURDIR":
                import os

                return os.path.dirname(self._doc.path)
            log.info(*log_info)
            return value_if_not_found
        return ret

    def _resolve_environment_variable(self, var_name, value_if_not_found, log_info):
        import os

        ret = os.environ.get(var_name, Sentinel.SENTINEL)
        if ret is Sentinel.SENTINEL:
            log.info(*log_info)
            return value_if_not_found
        return ret

    def _convert_robot_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

        if self.config is None:
            value = self._resolve_builtin(
                var_name,
                value_if_not_found,
                (
                    "Config not available while trying to convert robot variable: %s",
                    var_name,
                ),
            )
        else:
            robot_variables = self.config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
            value = robot_variables.get(var_name, Sentinel.SENTINEL)
            if value is Sentinel.SENTINEL:
                value = self._resolve_builtin(
                    var_name,
                    value_if_not_found,
                    ("Unable to find robot variable: %s", var_name),
                )

        value = str(value)
        return value

    def _convert_environment_variable(self, var_name, value_if_not_found):
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHON_ENV

        if self.config is None:
            value = self._resolve_environment_variable(
                var_name,
                value_if_not_found,
                (
                    "Config not available while trying to convert environment variable: %s",
                    var_name,
                ),
            )
        else:
            robot_env_vars = self.config.get_setting(OPTION_ROBOT_PYTHON_ENV, dict, {})
            value = robot_env_vars.get(var_name, Sentinel.SENTINEL)
            if value is Sentinel.SENTINEL:
                value = self._resolve_environment_variable(
                    var_name,
                    value_if_not_found,
                    ("Unable to find environment variable: %s", var_name),
                )

        value = str(value)
        return value

    @instance_cache
    def get_current_keyword_definition(self) -> Optional[IKeywordDefinition]:
        """
        Provides the current keyword even if we're in its arguments and not actually
        on the keyword itself.
        """
        current_keyword_definition_and_usage_info = (
            self.get_current_keyword_definition_and_usage_info()
        )
        if not current_keyword_definition_and_usage_info:
            return None
        return current_keyword_definition_and_usage_info[0]

    @instance_cache
    def get_current_keyword_usage_info(
        self,
    ) -> Optional[KeywordUsageInfo]:
        """
        Provides the current keyword even if we're in its arguments and not actually
        on the keyword itself.
        """
        from robotframework_ls.impl import ast_utils

        token_info = self.get_current_token()
        if token_info is None:
            return None
        cp: ICompletionContext = self

        while token_info.token.type == token_info.token.EOL:
            sel = cp.sel
            if sel.col > 0:
                cp = cp.create_copy_with_selection(sel.line, sel.col - 1)
                token_info = cp.get_current_token()
                if token_info is None:
                    return None
            else:
                break

        usage_info = ast_utils.create_keyword_usage_info_from_token(
            token_info.stack, token_info.node, token_info.token
        )
        return usage_info

    @instance_cache
    def get_current_keyword_definition_and_usage_info(
        self,
    ) -> Optional[Tuple[IKeywordDefinition, KeywordUsageInfo]]:
        """
        Provides the current keyword even if we're in its arguments and not actually
        on the keyword itself.
        """
        from robotframework_ls.impl.find_definition import find_keyword_definition

        usage_info = self.get_current_keyword_usage_info()
        if usage_info is not None:
            token = usage_info.token

            # token line is 1-based and col is 0-based (make both 0-based here).
            line = token.lineno - 1
            col = token.col_offset
            cp = self.create_copy_with_selection(line, col)
            definitions = find_keyword_definition(
                cp, TokenInfo(usage_info.stack, usage_info.node, usage_info.token)
            )
            if definitions and len(definitions) >= 1:
                definition: IKeywordDefinition = next(iter(definitions))
                return definition, usage_info
        return None

    @instance_cache
    def collect_dependency_graph(self) -> ICompletionContextDependencyGraph:
        from robotframework_ls.impl.completion_context_dependency_graph import (
            CompletionContextDependencyGraph,
        )

        return CompletionContextDependencyGraph.from_completion_context(self)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ICompletionContext = check_implements(self)
