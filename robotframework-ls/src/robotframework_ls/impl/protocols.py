import sys
from typing import (
    TypeVar,
    Any,
    Optional,
    List,
    Sequence,
    Tuple,
    Iterable,
    Generic,
    Iterator,
    Callable,
    Hashable,
    Dict,
    Set,
    Union,
)
from robocorp_ls_core.protocols import (
    Sentinel,
    IMonitor,
    IDocument,
    IWorkspace,
    IConfig,
    IDocumentSelection,
    ITestInfoFromSymbolsCacheTypedDict,
)
from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import TypedDict
import enum
from robocorp_ls_core.lsp import (
    LocationTypedDict,
    RangeTypedDict,
    MarkupContentTypedDict,
    CompletionItemTypedDict,
    LSPMessages,
)
import typing
from robocorp_ls_core.ordered_set import OrderedSet
from contextlib import contextmanager

if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol

T = TypeVar("T")
Y = TypeVar("Y", covariant=True)

# We don't want to import robot in this case (just do it when type-checking).
class IRobotToken(Protocol):
    SETTING_HEADER: str
    VARIABLE_HEADER: str
    TESTCASE_HEADER: str
    KEYWORD_HEADER: str
    COMMENT_HEADER: str

    TESTCASE_NAME: str
    KEYWORD_NAME: str

    DOCUMENTATION: str
    SUITE_SETUP: str
    SUITE_TEARDOWN: str
    METADATA: str
    TEST_SETUP: str
    TEST_TEARDOWN: str
    TEST_TEMPLATE: str
    TEST_TIMEOUT: str
    FORCE_TAGS: str
    DEFAULT_TAGS: str
    LIBRARY: str
    RESOURCE: str
    VARIABLES: str
    SETUP: str
    TEARDOWN: str
    TEMPLATE: str
    TIMEOUT: str
    TAGS: str
    ARGUMENTS: str
    # Use ´RETURN_SETTING` type instead of `RETURN`. `[Return]` is deprecated and
    # `RETURN` type will be used with `RETURN` statement in the future.
    RETURN: str
    RETURN_SETTING: str

    NAME: str
    VARIABLE: str
    ARGUMENT: str
    ASSIGN: str
    KEYWORD: str
    WITH_NAME: str
    FOR: str
    FOR_SEPARATOR: str
    END: str
    IF: str
    INLINE_IF: str
    ELSE_IF: str
    ELSE: str
    TRY: str
    EXCEPT: str
    FINALLY: str
    AS: str
    WHILE: str
    RETURN_STATEMENT: str
    CONTINUE: str
    BREAK: str

    SEPARATOR: str
    COMMENT: str
    CONTINUATION: str
    EOL: str
    EOS: str

    ERROR: str
    FATAL_ERROR: str

    type: str
    value: str
    lineno: int  # 1-based
    col_offset: int  # 0-based
    error: Any

    @property
    def end_col_offset(self) -> int:  # 0-based
        pass

    def tokenize_variables(self) -> Iterator["IRobotToken"]:
        pass


class IRobotVariableMatch(Protocol):
    string: str
    identifier: str
    base: Optional[str]
    items: Tuple[str, ...]
    start: int
    end: int

    @property
    def name(self) -> str:
        pass

    @property
    def before(self) -> str:
        pass

    @property
    def match(self) -> str:
        pass

    @property
    def after(self) -> str:
        pass


class INode(Protocol):
    type: str
    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int
    tokens: List[IRobotToken]

    def get_token(self, name: str) -> Optional[IRobotToken]:
        pass

    def get_tokens(self, name: str) -> List[IRobotToken]:
        pass


class ILibraryImportNode(INode, Protocol):
    name: str
    alias: Optional[str]
    args: Optional[Sequence[str]]


class IKeywordNode(INode, Protocol):
    name: str


class IResourceImportNode(INode, Protocol):
    name: str


class IVariableImportNode(INode, Protocol):
    name: str


class NodeInfo(Generic[Y]):
    stack: Tuple[INode, ...]
    node: Y

    __slots__ = ["stack", "node"]

    def __init__(self, stack, node):
        self.stack = stack
        self.node = node

    def __str__(self):
        return f"NodeInfo({self.node.__class__.__name__})"

    __repr__ = __str__


class TokenInfo:

    __slots__ = ["stack", "node", "token"]

    def __init__(self, stack: Tuple[INode, ...], node: INode, token: IRobotToken):
        self.stack = stack
        self.node = node
        self.token = token

    def __str__(self):
        return f"TokenInfo({self.token.value} -- in: {self.node.__class__.__name__})"

    __repr__ = __str__


class AdditionalVarInfo:

    CONTEXT_UNDEFINED = 0
    CONTEXT_EXPRESSION = 1

    __slots__ = ["var_identifier", "context", "extended_part"]

    def __init__(
        self,
        var_identifier: str = "",
        context: int = CONTEXT_UNDEFINED,
        extended_part: str = "",
    ):
        """
        :param var_identifier: One of: $,@,%
        """

        self.var_identifier = var_identifier
        self.context = context
        self.extended_part = extended_part

    def copy(self, **kwargs):
        new_kwargs = {
            "var_identifier": self.var_identifier,
            "context": self.context,
            "extended_part": self.extended_part,
        }
        new_kwargs.update(kwargs)
        return AdditionalVarInfo(**new_kwargs)

    def __str__(self):
        info = [f"AdditionalVarInfo({self.var_identifier}"]
        if self.context:
            info.append(f" -- ctx: {self.context}")
        if self.extended_part:
            info.append(f" -- extended: {self.extended_part}")
        info.append(")")
        return "".join(info)

    __repr__ = __str__


class VarTokenInfo:

    __slots__ = ["stack", "node", "token", "var_info"]

    def __init__(
        self,
        stack: Tuple[INode, ...],
        node: INode,
        token: IRobotToken,
        var_info: AdditionalVarInfo,
    ):
        self.stack = stack
        self.node = node
        self.token = token
        self.var_info = var_info

    def __str__(self):
        return f"VarTokenInfo({self.token.value} (in {self.node.__class__.__name__}) - {self.var_info})"

    __repr__ = __str__


class KeywordUsageInfo:
    __slots__ = ["stack", "node", "token", "name", "_is_argument_usage", "prefix"]

    def __init__(
        self,
        stack: Tuple[INode, ...],
        node: INode,
        token: IRobotToken,
        name: str,
        is_argument_usage: bool = False,
        prefix: str = "",
    ):
        self.stack = stack
        self.node = node
        self.token = token  # This is actually the keyword name token.
        self.name = name
        self._is_argument_usage = is_argument_usage
        self.prefix = prefix

    def __repr__(self):
        if self._is_argument_usage:
            return f"KeywordUsageInfo({self.name} - {self.node.__class__.__name__} (argument usage))"
        else:
            return f"KeywordUsageInfo({self.name} - {self.node.__class__.__name__})"

    __str__ = __repr__


class IKeywordArg(Protocol):
    @property
    def original_arg(self) -> str:
        pass

    @property
    def arg_name(self) -> str:
        pass

    @property
    def is_keyword_arg(self) -> bool:
        pass

    @property
    def is_star_arg(self) -> bool:
        pass

    def is_arg_type_set(self) -> bool:
        pass

    @property
    def arg_type(self) -> Optional[str]:
        pass

    def is_default_value_set(self) -> bool:
        pass

    @property
    def default_value(self) -> Optional[str]:
        pass


class ILibraryDoc(Protocol):
    filename: str
    name: str
    source: str
    symbols_cache: Optional["ISymbolsCache"]
    inits: list
    doc_format: str
    keywords: List["IKeywordDoc"]


class ILibraryDocConversions(ILibraryDoc):
    """
    Note: these are actually part of the basic library doc but we
    put it in a different interface because clients usually shouldn't
    use it (it's controlled by the libspec manager).
    """

    def convert_docs_to_html(self):
        pass

    def convert_docs_to_markdown(self):
        pass


class IKeywordDoc(Protocol):
    name: str
    tags: Tuple[str, ...]
    lineno: int
    doc: str

    @property
    def args(self) -> Tuple[IKeywordArg, ...]:
        pass

    @property
    def libdoc(self) -> ILibraryDoc:
        pass

    @property
    def deprecated(self) -> bool:
        pass

    @property
    def source(self) -> str:
        pass

    @property
    def doc_format(self) -> str:
        pass

    def to_dictionary(self) -> dict:
        pass


class ILibraryDocOrError(Protocol):
    library_doc: Optional[ILibraryDoc]
    error: Optional[str]


class IRobotDocument(IDocument, Protocol):
    def get_type(self) -> str:
        pass

    def get_ast(self) -> Any:
        pass

    def get_python_ast(self) -> Optional[Any]:
        pass

    def get_yaml_contents(self) -> Optional[Any]:
        pass

    symbols_cache: Optional["ISymbolsCache"]


class ISymbolsJsonListEntry(TypedDict):
    name: str
    kind: int  # SymbolKind
    location: LocationTypedDict
    containerName: str


class ISymbolKeywordInfo(Protocol):
    name: str

    def get_documentation(self) -> MarkupContentTypedDict:
        """
        Note: It should be computed on demand (and can be slow).
        """


class ISymbolsCache(Protocol):
    def get_uri(self) -> Optional[str]:
        """
        If we're referencing a library (and have the symbols from a libspec),
        the uri may be None.
        """

    def has_keyword_usage(self, normalized_keyword_name: str) -> bool:
        pass

    def has_global_variable_definition(self, normalized_variable_name: str) -> bool:
        pass

    def has_variable_reference(self, normalized_variable_name: str) -> bool:
        pass

    def get_json_list(self) -> List[ISymbolsJsonListEntry]:
        pass

    def get_library_info(self) -> Optional[ILibraryDoc]:
        pass

    def get_doc(self) -> Optional[IRobotDocument]:
        pass

    def get_test_info(self) -> Optional[List[ITestInfoFromSymbolsCacheTypedDict]]:
        pass

    def iter_keyword_info(self) -> Iterator[ISymbolKeywordInfo]:
        pass


class ICompletionContextWorkspaceCaches(Protocol):
    cache_hits: int

    def on_file_changed(self, filename: str):
        pass

    def on_updated_document(self, uri: str, document: Optional[IRobotDocument]):
        pass

    def clear_caches(self):
        pass

    def dispose(self):
        pass

    def get_cached_dependency_graph(
        self, cache_key: Hashable
    ) -> Optional["ICompletionContextDependencyGraph"]:
        pass

    @contextmanager
    def invalidation_tracker(self):
        """
        Note that it's possible that changes happen in-flight. This means that
        we must track changes while the dependency graph is being calculated.

        So, one must do something as:

        with caches.invalidation_tracker() as invalidation_tracker:
            ... compute dependency graph
            caches.cache_dependency_graph(cache_key, dependency_graph, invalidation_tracker)
        """

    def cache_dependency_graph(
        self,
        cache_key: Hashable,
        dependency_graph: "ICompletionContextDependencyGraph",
        invalidation_tracker,
    ) -> None:
        pass


class IRobotWorkspace(IWorkspace, Protocol):
    completion_context_workspace_caches: ICompletionContextWorkspaceCaches
    libspec_manager: Any

    def iter_all_doc_uris_in_workspace(
        self, extensions: Tuple[str, ...]
    ) -> Iterable[str]:
        pass


class IKeywordFound(Protocol):
    """
    :ivar completion_context:
        This may be a new completion context, created when a new document is
        being analyzed (the keyword was created for that completion context).
        For libraries the initial completion context is passed.
    :ivar source:
        Source where the keyword was found.
    :ivar lineno:
        Line where it was found (0-based).
    """

    @property
    def keyword_name(self) -> str:
        pass

    @property
    def keyword_ast(self) -> Optional[INode]:
        """
        Only available when we do have a keyword AST (i.e.: not for library
        keywords).
        """

    @property
    def keyword_args(self) -> Sequence[IKeywordArg]:
        pass

    def is_deprecated(self) -> bool:
        pass

    def compute_docs_with_signature(self) -> MarkupContentTypedDict:
        pass

    def compute_docs_without_signature(self) -> MarkupContentTypedDict:
        pass

    completion_context: Optional["ICompletionContext"]

    completion_item_kind: int = -1

    @property
    def source(self) -> str:
        """
        Provides the filesystem location where the keyword was found.
        """

    @property
    def lineno(self) -> int:
        pass

    @property
    def end_lineno(self) -> int:
        pass

    @property
    def col_offset(self) -> int:
        pass

    @property
    def end_col_offset(self) -> int:
        pass

    @property
    def library_name(self) -> Optional[str]:
        # If it's a library, this is the name of the library.
        pass

    @property
    def resource_name(self) -> Optional[str]:
        # If it's a resource, this is the basename of the resource without the extension.
        pass

    @property
    def library_alias(self) -> Optional[str]:
        pass

    # These are added if possible if there's some range to include the
    # full scope of the keyword. It should always include
    # the lineno/end_lineno range (so, it's a superset).

    @property
    def scope_lineno(self) -> Optional[int]:
        pass

    @property
    def scope_end_lineno(self) -> Optional[int]:
        pass

    @property
    def scope_col_offset(self) -> Optional[int]:
        pass

    @property
    def scope_end_col_offset(self) -> Optional[int]:
        pass


class IKeywordCollector(Protocol):
    def accepts(self, keyword_name: str) -> bool:
        """
        :param keyword_name:
            The name of the keyword to be accepted or not.
        :return bool:
            If the return is True, on_keyword(...) is called (otherwise it's not
            called).
        """

    def on_keyword(self, keyword_found: IKeywordFound):
        """
        :param IKeywordFound keyword_found:
        """

    def on_resolved_library(
        self,
        completion_context: "ICompletionContext",
        library_node: Optional[INode],
        library_doc: "ILibraryDoc",
    ):
        pass

    def on_unresolved_library(
        self,
        completion_context: "ICompletionContext",
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass

    def on_unresolved_resource(
        self,
        completion_context: "ICompletionContext",
        resource_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass


class AbstractKeywordCollector:
    def on_resolved_library(
        self,
        completion_context: "ICompletionContext",
        library_node,
        library_doc: ILibraryDoc,
    ):
        pass

    def on_unresolved_library(
        self,
        completion_context: "ICompletionContext",
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass

    def on_unresolved_resource(
        self,
        completion_context: "ICompletionContext",
        resource_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass


class IDefinition(Protocol):

    keyword_name: str = ""  # Can be empty if it's not found as a keyword.

    # Note: Could be None (i.e.: we found it in a library spec file which doesn't have the source).
    source: str = ""

    # Note: if we found it in a library spec file which doesn't have the lineno, it should be 0
    lineno: int = 0

    # Note: if we found it in a library spec file which doesn't have the lineno, it should be 0
    end_lineno: int = 0

    col_offset: int = 0

    end_col_offset: int = 0

    # These are added if possible if there's some range to include the
    # full scope (of a keyword, test, etc). It should always include
    # the lineno/end_lineno range (so, it's a superset).
    scope_lineno: Optional[int] = None
    scope_end_lineno: Optional[int] = None
    scope_col_offset: Optional[int] = None
    scope_end_col_offset: Optional[int] = None

    def hover_docs(self) -> MarkupContentTypedDict:
        pass


class IKeywordDefinition(IDefinition, Protocol):

    keyword_found: IKeywordFound


class IVariableDefinition(IDefinition, Protocol):

    variable_found: "IVariableFound"


def cast_to_keyword_definition(definition: IDefinition) -> Optional[IKeywordDefinition]:
    if hasattr(definition, "keyword_found"):
        return typing.cast(IKeywordDefinition, definition)
    return None


def cast_to_variable_definition(
    definition: IDefinition,
) -> Optional[IVariableDefinition]:
    if hasattr(definition, "variable_found"):
        return typing.cast(IVariableDefinition, definition)
    return None


class IBaseCompletionContext(Protocol):
    @property
    def monitor(self) -> Optional[IMonitor]:
        pass

    @property
    def workspace(self) -> IRobotWorkspace:
        pass

    @property
    def config(self) -> Optional[IConfig]:
        pass

    def check_cancelled(self) -> None:
        pass


class CompletionType(enum.Enum):
    regular = 1
    shell = 2


class LibraryDependencyInfo:
    def __init__(
        self,
        name: str,
        alias: Optional[str],
        builtin: bool,
        args: Optional[str],
        node: Optional[ILibraryImportNode],
    ):
        """
        :param builtin:
            Note that builtin should only be set == True if it's actually known
            that it's a builtin, otherwise it should be set to False (in which
            case it's computed internally if it's builtin or not).
        """
        self.name = name
        self.alias = alias
        self.builtin = builtin
        self.args = args
        self.node = node

    def to_dict(self):
        ret = {
            "name": self.name,
        }
        if self.alias:
            ret["alias"] = self.alias
        if self.builtin:
            ret["builtin"] = self.builtin
        if self.args:
            ret["args"] = self.args
        return ret


class ISymbolsCacheReverseIndex(Protocol):
    def get_global_variable_uri_definitions(
        self, normalized_var_name: str
    ) -> Optional[Set[str]]:
        pass

    def has_global_variable(self, normalized_var_name: str) -> bool:
        pass


class ICompletionContextDependencyGraph(Protocol):
    def add_library_infos(
        self,
        doc_uri: str,
        library_infos: OrderedSet[LibraryDependencyInfo],
    ):
        pass

    def add_resource_infos(
        self,
        doc_uri: str,
        resource_imports_as_docs: Sequence[
            Tuple[IResourceImportNode, Optional[IRobotDocument]]
        ],
    ):
        pass

    def add_variable_infos(
        self,
        doc_uri: str,
        new_variable_imports: Sequence[
            Tuple[IVariableImportNode, Optional[IRobotDocument]]
        ],
    ):
        pass

    def get_root_doc(self) -> IRobotDocument:
        pass

    def iter_libraries(self, doc_uri: str) -> Iterator[LibraryDependencyInfo]:
        """
        Provides an iterator(doc_uri, library_dependency_infos)
        """

    def iter_all_libraries(self) -> Iterator[LibraryDependencyInfo]:
        pass

    def iter_resource_imports_with_docs(
        self, doc_uri: str
    ) -> Iterator[Tuple[IResourceImportNode, Optional[IRobotDocument]]]:
        pass

    def iter_all_resource_imports_with_docs(
        self,
    ) -> Iterator[Tuple[IResourceImportNode, Optional[IRobotDocument]]]:
        pass

    def iter_variable_imports_as_docs(
        self, doc_uri: str
    ) -> Iterator[Tuple[IVariableImportNode, Optional[IRobotDocument]]]:
        pass

    def iter_all_variable_imports_as_docs(
        self,
    ) -> Iterator[Tuple[IVariableImportNode, Optional[IRobotDocument]]]:
        pass

    def to_dict(self) -> dict:
        pass

    def do_invalidate_on_uri_change(self, uri: str) -> bool:
        pass


class IVariablesFromArgumentsFileLoader(Protocol):
    def get_variables(self) -> Tuple["IVariableFound", ...]:
        pass


class ILocalizationInfo(Protocol):
    def __init__(self, language_codes: Union[Tuple[str, ...], str]):
        pass

    @property
    def language_codes(self) -> Tuple[str, ...]:
        pass

    def iter_bdd_prefixes_on_read(self) -> Iterator[str]:
        """
        Note that we specify the reason for iterating because for instance, when
        writing code we could want just the completions for the specified
        language in the file and while reading (i.e.: analyzing) we'd want it
        for all languages.
        """

    def iter_languages_on_write(
        self,
    ) -> Iterator[Any]:  # Actually Iterator[robot.api.Language]
        """
        Provides the languages used when writing a doc (i.e.: completions, ...).
        """


class ICompletionContext(Protocol):
    tracing: bool

    def __init__(
        self,
        doc,
        line=Sentinel.SENTINEL,
        col=Sentinel.SENTINEL,
        workspace=None,
        config=None,
        memo=None,
        monitor: IMonitor = NULL,
        variables_from_arguments_files_loader: Sequence[
            IVariablesFromArgumentsFileLoader
        ] = (),
    ) -> None:
        pass

    def resolve_completion_item(
        self, data, completion_item: CompletionItemTypedDict, monaco: bool = False
    ) -> None:
        pass

    @property
    def lsp_messages(
        self,
    ) -> Optional[LSPMessages]:
        pass

    @property
    def variables_from_arguments_files_loader(
        self,
    ) -> Sequence[IVariablesFromArgumentsFileLoader]:
        pass

    @property
    def type(self) -> CompletionType:
        pass

    @property
    def monitor(self) -> IMonitor:
        pass

    def check_cancelled(self):
        pass

    def create_copy_with_selection(self, line: int, col: int) -> "ICompletionContext":
        pass

    def create_copy(self, doc: IRobotDocument) -> "ICompletionContext":
        pass

    def create_copy_with_config(self, config: IConfig) -> "ICompletionContext":
        pass

    def create_copy_doc_line_col(
        self, doc: IRobotDocument, line: int, col: int
    ) -> "ICompletionContext":
        pass

    @property
    def original_doc(self) -> IRobotDocument:
        pass

    @property
    def original_sel(self) -> Any:
        pass

    @property
    def doc(self) -> IRobotDocument:
        pass

    @property
    def sel(self) -> IDocumentSelection:
        pass

    @property
    def memo(self) -> Any:
        pass

    @property
    def config(self) -> Optional[IConfig]:
        pass

    @property
    def workspace(self) -> IRobotWorkspace:
        pass

    def get_type(self) -> Any:
        pass

    def get_ast(self) -> Any:
        pass

    def get_ast_current_section(self) -> Optional[INode]:
        """
        :rtype: robot.parsing.model.blocks.Section|NoneType
        """

    def get_current_section_name(self) -> Optional[str]:
        pass

    def get_current_token(self) -> Optional[TokenInfo]:
        pass

    def get_all_variables(self) -> Tuple[NodeInfo, ...]:
        pass

    def get_doc_normalized_var_name_to_var_found(self) -> Dict[str, "IVariableFound"]:
        pass

    def get_settings_normalized_var_name_to_var_found(
        self,
    ) -> Dict[str, "IVariableFound"]:
        pass

    def get_builtins_normalized_var_name_to_var_found(
        self, resolved
    ) -> Dict[str, "IVariableFound"]:
        pass

    def get_arguments_files_normalized_var_name_to_var_found(
        self,
    ) -> Dict[str, "IVariableFound"]:
        pass

    def get_current_variable(self, section=None) -> Optional[VarTokenInfo]:
        """
        Provides the current variable token. Note that it won't include '{' nor '}'.
        """

    def get_resource_import_as_doc(
        self, resource_import: INode, check_as_module: bool = False
    ) -> Optional[IRobotDocument]:
        pass

    def get_variable_imports(self) -> Tuple[INode, ...]:
        pass

    def get_variable_import_as_doc(self, variables_import) -> Optional[IRobotDocument]:
        pass

    def get_current_keyword_definition(self) -> Optional[IKeywordDefinition]:
        pass

    def get_resource_imports(
        self,
    ) -> Tuple[IResourceImportNode, ...]:
        pass

    def get_resource_imports_as_docs(
        self,
    ) -> Tuple[Tuple[IResourceImportNode, Optional[IRobotDocument]], ...]:
        pass

    def get_resource_inits_as_docs(self) -> Tuple[IRobotDocument, ...]:
        pass

    def get_variable_imports_as_docs(
        self,
    ) -> Tuple[Tuple[IVariableImportNode, Optional[IRobotDocument]], ...]:
        pass

    def get_imported_libraries(self) -> Tuple[ILibraryImportNode, ...]:
        pass

    def token_value_resolving_variables(self, token: IRobotToken) -> str:
        pass

    def token_value_and_unresolved_resolving_variables(
        self, token: IRobotToken
    ) -> Tuple[str, Tuple[Tuple[IRobotToken, str], ...]]:
        pass

    def get_current_keyword_definition_and_usage_info(
        self,
    ) -> Optional[Tuple[IKeywordDefinition, KeywordUsageInfo]]:
        pass

    def get_current_keyword_usage_info(
        self,
    ) -> Optional[KeywordUsageInfo]:
        pass

    def assign_documentation_resolve(
        self,
        completion_item: CompletionItemTypedDict,
        compute_documentation: Callable[[], MarkupContentTypedDict],
    ) -> None:
        pass

    def collect_dependency_graph(self) -> ICompletionContextDependencyGraph:
        pass

    def iter_dependency_and_init_resource_docs(
        self, dependency_graph
    ) -> Iterator[IRobotDocument]:
        pass

    def obtain_symbols_cache_reverse_index(self) -> Optional[ISymbolsCacheReverseIndex]:
        pass

    def get_ast_localization_info(self) -> ILocalizationInfo:
        pass


class VariableKind:
    VARIABLE = "Variable"
    BUILTIN = "Builtin Variable"
    ARGUMENT = "Argument"
    ENV_VARIABLE = "Environment Variable"
    SETTINGS = "Variable (settings)"
    PYTHON = "Variable (python)"
    YAML = "Variable (yaml)"
    ARGUMENTS_FILE = "Arguments file"
    LOCAL_ASSIGN_VARIABLE = "Variable (local assign)"
    LOCAL_SET_VARIABLE = "Variable (local set)"
    TASK_SET_VARIABLE = "Variable (task set)"
    TEST_SET_VARIABLE = "Variable (test set)"
    SUITE_SET_VARIABLE = "Variable (suite set)"
    GLOBAL_SET_VARIABLE = "Variable (global)"
    ENV_SET_VARIABLE = "Variable (environment)"


LOCAL_ASSIGNS_VARIABLE_KIND = {
    VariableKind.ARGUMENT,
    VariableKind.LOCAL_ASSIGN_VARIABLE,
    VariableKind.LOCAL_SET_VARIABLE,
}


class IVariableFound(Protocol):
    """
    :ivar variable_name:
        This is the value that we should use when completing.
        It's the name of the variable without `${}` chars.

    :ivar variable_value:
        The value of the variable -- in general used to show information
        regarding that variable to the user.

    :ivar completion_context:
        This may be a new completion context, created when a new document is
        being analyzed (the variable was created for that completion context).

    :ivar source:
        Source where the variable was found.

    :ivar lineno:
        Line where it was found (0-based).

    :ivar stack:
        The stack where the variable was found (only available if it was
        found in a robot file where the ast is available -- i.e.: settings,
        yaml, python, etc. variables don't have a stack available).
    """

    variable_name: str = ""
    variable_value: str = ""
    variable_kind: str = VariableKind.VARIABLE
    completion_context: Optional[ICompletionContext] = None
    stack: Optional[Tuple[INode, ...]] = None

    @property
    def is_local_variable(self) -> bool:
        pass

    @property
    def source(self) -> str:
        pass

    # Note: line/offsets 0-based.
    @property
    def lineno(self) -> int:
        pass

    @property
    def end_lineno(self) -> int:
        pass

    @property
    def col_offset(self) -> int:
        pass

    @property
    def end_col_offset(self) -> int:
        pass


class IVariablesCollector(Protocol):
    def accepts(self, variable_name: str) -> bool:
        """
        :param variable_name:
            The name of the variable (i.e.: ${some_var}).
        """

    def on_variable(self, variable_found: IVariableFound):
        pass

    def on_unresolved_variable_import(
        self,
        completion_context: "ICompletionContext",
        variable_import_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass

    def on_env_variable(self, variable_found: IVariableFound):
        """
        Called for environment variables using the
        'Set Keyword Variable' keyword.

        Note: doesn't call `accepts` first.
        """


class AbstractVariablesCollector:
    def on_env_variable(self, variable_found: IVariableFound):
        pass

    def on_unresolved_variable_import(
        self,
        completion_context: "ICompletionContext",
        variable_import_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        pass


class EvaluatableExpressionTypedDict(TypedDict):
    range: RangeTypedDict
    expression: Optional[str]


class IOnDependencyChanged(Protocol):
    def __call__(self, uri: str):
        pass
