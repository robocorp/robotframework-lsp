import sys
import os
from typing import (
    Optional,
    Any,
    List,
    Tuple,
    Set,
    Callable,
    Dict,
    Iterator,
    Sequence,
)

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.lsp import (
    CompletionItemTypedDict,
    MarkupContentTypedDict,
    LSPMessages,
)
from robocorp_ls_core.protocols import (
    IMonitor,
    Sentinel,
    IConfig,
    IDocumentSelection,
    IWorkspace,
)
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
    INode,
    IVariableImportNode,
    VarTokenInfo,
    IVariablesFromArgumentsFileLoader,
    IVariablesFromVariablesFileLoader,
    IVariableFound,
    NodeInfo,
    ISymbolsCacheReverseIndex,
    ILocalizationInfo,
)
from robotframework_ls.impl.robot_workspace import RobotDocument
from robocorp_ls_core import uris
import itertools
from functools import partial
import typing
from robotframework_ls.impl.robot_version import get_robot_major_version


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
        line=Sentinel.SENTINEL,  # 0-based
        col=Sentinel.SENTINEL,  # 0-based
        workspace: Optional[IWorkspace] = None,
        config: Optional[IConfig] = None,
        memo: Optional[_Memo] = None,
        monitor: Optional[IMonitor] = NULL,
        variables_from_arguments_files_loader: Sequence[
            IVariablesFromArgumentsFileLoader
        ] = (),
        variables_from_variables_files_loader: Sequence[
            IVariablesFromVariablesFileLoader
        ] = (),
        lsp_messages: Optional[LSPMessages] = None,
        tracing: bool = False,
    ) -> None:
        if col is Sentinel.SENTINEL or line is Sentinel.SENTINEL:
            assert col is Sentinel.SENTINEL, (
                "Either line and col are not set, or both are set. Found: (%s, %s)"
                % (
                    line,
                    col,
                )
            )
            assert line is Sentinel.SENTINEL, (
                "Either line and col are not set, or both are set. Found: (%s, %s)"
                % (
                    line,
                    col,
                )
            )

            # If both are not set, use the doc len as the selection.
            line, col = doc.get_last_line_col()

        memo = _Memo() if memo is None else memo

        sel = doc.selection(line, col)

        self._doc = doc
        self._sel = sel
        self._workspace = typing.cast(Optional[IRobotWorkspace], workspace)
        self._config = config
        self._memo = memo
        self._original_ctx: Optional[CompletionContext] = None
        self._monitor = monitor or NULL
        self.type = CompletionType.regular
        self.lsp_messages = lsp_messages
        self.tracing = tracing

        # Note: it's None until it's requested in obtain_symbols_cache_reverse_index().
        # At that point it's obtained and synchronized accordingly (then, any copy
        # from this context should use that same version without synchronizing again).
        self._symbols_cache_reverse_index: Optional[ISymbolsCacheReverseIndex] = None

        self._id_to_compute_documentation: Dict[
            int, Callable[[], MarkupContentTypedDict]
        ] = {}
        self.variables_from_arguments_files_loader = (
            variables_from_arguments_files_loader
        )
        self.variables_from_variables_files_loader = (
            variables_from_variables_files_loader
        )

    def __str__(self):
        return f"CompletionContext({self.doc.uri})"

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
        return self.create_copy_doc_line_col(doc=self._doc, line=line, col=col)

    def create_copy(self, doc: IRobotDocument) -> ICompletionContext:
        return self.create_copy_doc_line_col(doc, line=0, col=0)

    def create_copy_with_config(self, config: IConfig) -> "ICompletionContext":
        return self.create_copy_doc_line_col(
            doc=self._doc, line=self.sel.line, col=self.sel.col, config=config
        )

    def create_copy_doc_line_col(
        self, doc: IRobotDocument, line: int, col: int, config: Optional[IConfig] = None
    ) -> ICompletionContext:
        if config is None:
            config = self._config
        ctx = CompletionContext(
            doc,
            line=line,
            col=col,
            workspace=self._workspace,
            config=config,
            memo=self._memo,
            monitor=self._monitor,
            variables_from_arguments_files_loader=self.variables_from_arguments_files_loader,
            variables_from_variables_files_loader=self.variables_from_variables_files_loader,
            lsp_messages=self.lsp_messages,
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
        assert self._workspace
        return self._workspace

    @instance_cache
    def get_type(self) -> Any:
        return self.doc.get_type()

    @instance_cache
    def get_ast(self) -> Any:
        return self.doc.get_ast()

    @instance_cache
    def get_ast_current_section(self) -> Optional[INode]:
        """
        :rtype: robot.parsing.model.blocks.Section|NoneType
        """
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        section = ast_utils.find_section(ast, self.sel.line)
        return section

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

    @instance_cache
    def get_current_token(self) -> Optional[TokenInfo]:
        from robotframework_ls.impl import ast_utils

        section = self.get_ast_current_section()
        if section is None:
            return None
        return ast_utils.find_token(section, self.sel.line, self.sel.col)

    def get_all_variables(self) -> Tuple[NodeInfo, ...]:
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        return tuple(ast_utils.iter_variables(ast))

    @instance_cache
    def get_doc_normalized_var_name_to_var_found(self) -> Dict[str, IVariableFound]:
        from robotframework_ls.impl import ast_utils
        from robotframework_ls.impl.variable_resolve import robot_search_variable
        from robot.api import Token
        from robotframework_ls.impl.variable_types import VariableFoundFromToken
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        ret: Dict[str, IVariableFound] = {}
        for variable_node_info in self.get_all_variables():
            variable_node = variable_node_info.node
            token = variable_node.get_token(Token.VARIABLE)
            if token is None:
                continue

            variable_match = robot_search_variable(token.value)
            # Filter out empty base
            if variable_match is None or not variable_match.base:
                continue

            base_token = ast_utils.convert_variable_match_base_to_token(
                token, variable_match
            )
            ret[normalize_robot_name(variable_match.base)] = VariableFoundFromToken(
                self,
                base_token,
                variable_node.value,
                variable_name=variable_match.base,
                stack=variable_node_info.stack,
            )

        return ret

    @instance_cache
    def get_settings_normalized_var_name_to_var_found(
        self,
    ) -> Dict[str, IVariableFound]:
        from robotframework_ls.impl.text_utilities import normalize_robot_name
        from robotframework_ls.impl.variable_types import VariableFoundFromSettings

        ret: Dict[str, IVariableFound] = {}

        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

        config = self.config
        if config is not None:
            robot_variables = config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
            for key, val in robot_variables.items():
                ret[normalize_robot_name(key)] = VariableFoundFromSettings(key, val)

        return ret

    @instance_cache
    def get_builtins_normalized_var_name_to_var_found(
        self, resolved
    ) -> Dict[str, IVariableFound]:
        from robotframework_ls.impl.text_utilities import normalize_robot_name
        from robotframework_ls.impl.variable_types import VariableFoundFromBuiltins
        from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES_RESOLVED

        ret: Dict[str, IVariableFound] = {}

        from robotframework_ls.impl.robot_constants import get_builtin_variables

        for key, val in get_builtin_variables():
            ret[normalize_robot_name(key)] = VariableFoundFromBuiltins(key, val)

        if resolved:
            for key, val in BUILTIN_VARIABLES_RESOLVED.items():
                # Provide a resolved value for the ones we can resolve.
                ret[normalize_robot_name(key)] = VariableFoundFromBuiltins(key, val)

        return ret

    def get_arguments_files_normalized_var_name_to_var_found(
        self,
    ) -> Dict[str, IVariableFound]:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        ret: Dict[str, IVariableFound] = {}

        if not self.variables_from_arguments_files_loader:
            return ret

        for c in self.variables_from_arguments_files_loader:
            for variable in c.get_variables():
                ret[normalize_robot_name(variable.variable_name)] = variable

        return ret

    def get_variables_files_normalized_var_name_to_var_found(
        self,
    ) -> Dict[str, IVariableFound]:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        ret: Dict[str, IVariableFound] = {}

        if not self.variables_from_variables_files_loader:
            return ret

        for c in self.variables_from_variables_files_loader:
            for variable in c.get_variables():
                ret[normalize_robot_name(variable.variable_name)] = variable

        return ret

    @instance_cache
    def get_current_variable(self, section=None) -> Optional[VarTokenInfo]:
        """
        Provides the current variable token. Note that it won't include '{' nor '}'.
        """
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
                if self.tracing:
                    log.debug(
                        "Found import node (in get_imported_libraries): %s (alias: %s)",
                        library_import.node.name,
                        library_import.node.alias,
                    )
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
    def get_variable_imports(self) -> Tuple[INode, ...]:
        from robotframework_ls.impl import ast_utils

        ast = self.get_ast()
        ret = []
        for resource in ast_utils.iter_variable_imports(ast):
            if resource.node.name:
                ret.append(resource.node)
        return tuple(ret)

    def token_value_resolving_variables(self, token: IRobotToken) -> str:
        from robotframework_ls.impl.variable_resolve import ResolveVariablesContext

        return ResolveVariablesContext(self).token_value_resolving_variables(token)

    def token_value_and_unresolved_resolving_variables(
        self, token: IRobotToken
    ) -> Tuple[str, Tuple[Tuple[IRobotToken, str], ...]]:
        from robotframework_ls.impl.variable_resolve import ResolveVariablesContext

        return ResolveVariablesContext(
            self
        ).token_value_and_unresolved_resolving_variables(token)

    @instance_cache
    def get_resource_import_as_doc(
        self, resource_import: INode, check_as_module=False
    ) -> Optional[IRobotDocument]:
        """
        :param check_as_module: If true we'll also check if we have matches as a
            python module (i.e.: Variable    my.mod   will be searched as `my/mod.py`).
        """
        from robot.api import Token
        from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

        ws = self.workspace
        token = resource_import.get_token(Token.NAME)
        if token is not None:
            name_with_resolved_vars = self.token_value_resolving_variables(token)
            check: Tuple[str, ...]
            if check_as_module:
                name_with_os_sep = name_with_resolved_vars.replace(".", os.sep)
                check = (
                    name_with_resolved_vars,
                    name_with_os_sep + ".py",
                    f"{name_with_os_sep}{os.sep}__init__.py",
                )
            else:
                check = (name_with_resolved_vars,)
            for n in check:
                if not os.path.isabs(n):
                    # It's a relative resource, resolve its location based on the
                    # current file.
                    check_paths = [
                        os.path.normpath(
                            os.path.join(os.path.dirname(self.doc.path), n)
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
                                        n,
                                    )
                                )
                            )

                    for path in sys.path:
                        check_paths.append(
                            os.path.normpath(
                                os.path.join(
                                    path,
                                    n,
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
                    check_paths = [n]

                for resource_path in check_paths:
                    doc_uri = uris.from_fs_path(resource_path)
                    resource_doc = ws.get_document(doc_uri, accept_from_file=True)
                    if resource_doc is None:
                        continue
                    return typing.cast(IRobotDocument, resource_doc)

            log.info(
                "Unable to find: %s (checked paths: %s)",
                name_with_resolved_vars,
                check_paths,
            )

        return None

    def get_variable_import_as_doc(
        self, variables_import: INode
    ) -> Optional[IRobotDocument]:
        check_as_module = False
        if get_robot_major_version() >= 5:
            check_as_module = True
        return self.get_resource_import_as_doc(variables_import, check_as_module)

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
    def get_resource_inits_as_docs(self) -> Tuple[IRobotDocument, ...]:
        doc = self.doc
        path = doc.path
        if not path:
            return ()

        if not os.path.isabs(path):
            # i.e.: We can't deal with untitled...
            return ()

        parent_dir_path = os.path.dirname(path)

        ret: List[IRobotDocument] = []
        ws = self.workspace
        folder_root_paths = ws.get_folder_paths()

        for root_path in folder_root_paths:
            if parent_dir_path.startswith(root_path):
                stop_condition = lambda parent_dir_path: parent_dir_path == root_path
                break

        else:
            # We're dealing with a resource out of the workspace root,
            # so, let's stop at max range.
            next_i: "partial[int]" = partial(next, itertools.count())
            stop_condition = lambda parent_dir_path: next_i() >= 6

        initial_parent_path = parent_dir_path

        def iter_inits():
            parent_dir_path = initial_parent_path
            while True:
                yield os.path.join(parent_dir_path, "__init__.robot")

                if stop_condition(parent_dir_path):
                    break

                initial_len = len(parent_dir_path)
                parent_dir_path = os.path.dirname(parent_dir_path)
                if initial_len == len(parent_dir_path) or not len(parent_dir_path):
                    break

        for resource_path in iter_inits():
            doc_uri = uris.from_fs_path(resource_path)
            resource_doc = ws.get_document(doc_uri, accept_from_file=True)
            if resource_doc is not None:
                ret.append(typing.cast(IRobotDocument, resource_doc))
        return tuple(ret)

    def iter_dependency_and_init_resource_docs(
        self, dependency_graph
    ) -> Iterator[IRobotDocument]:
        visited = set()
        for resource_doc in itertools.chain(
            (d[1] for d in dependency_graph.iter_all_resource_imports_with_docs()),
            iter(self.get_resource_inits_as_docs()),
        ):
            if resource_doc is not None:
                if resource_doc.uri not in visited:
                    visited.add(resource_doc.uri)
                    yield resource_doc

    @instance_cache
    def get_variable_imports_as_docs(
        self,
    ) -> Tuple[Tuple[IVariableImportNode, Optional[IRobotDocument]], ...]:
        ret: List[Tuple[IResourceImportNode, Optional[IRobotDocument]]] = []

        variable_imports = self.get_variable_imports()
        for variable_import in variable_imports:
            variable_doc = self.get_variable_import_as_doc(variable_import)
            ret.append((variable_import, variable_doc))

        return tuple(ret)

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
            if definitions:
                definition: IKeywordDefinition = next(iter(definitions))
                return definition, usage_info
        return None

    @instance_cache
    def collect_dependency_graph(self) -> ICompletionContextDependencyGraph:
        from robotframework_ls.impl.completion_context_dependency_graph import (
            CompletionContextDependencyGraph,
        )

        return CompletionContextDependencyGraph.from_completion_context(self)

    def obtain_symbols_cache_reverse_index(self) -> Optional[ISymbolsCacheReverseIndex]:
        original_ctx = self._original_ctx
        if original_ctx is not None:
            # The parent must be the one containing it.
            return original_ctx.obtain_symbols_cache_reverse_index()

        symbols_cache_reverse_index = self._symbols_cache_reverse_index
        if symbols_cache_reverse_index is not None:
            # Should be already synchronized in this case.
            return symbols_cache_reverse_index

        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        workspace: Optional[RobotWorkspace] = typing.cast(
            Optional[RobotWorkspace], self.workspace
        )
        if not workspace:
            return None

        workspace_indexer = workspace.workspace_indexer
        if not workspace_indexer:
            return None

        symbols_cache_reverse_index = workspace_indexer.symbols_cache_reverse_index
        symbols_cache_reverse_index.synchronize(self)
        return symbols_cache_reverse_index

    def get_ast_localization_info(self) -> ILocalizationInfo:
        from robotframework_ls.impl import ast_utils

        return ast_utils.get_localization_info_from_model(self.get_ast())

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ICompletionContext = check_implements(self)
