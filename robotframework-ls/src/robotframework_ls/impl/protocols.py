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
from collections import namedtuple
import enum
from robocorp_ls_core.lsp import (
    LocationTypedDict,
    RangeTypedDict,
    MarkupContentTypedDict,
    CompletionItemTypedDict,
)
import typing

if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol

T = TypeVar("T")
Y = TypeVar("Y", covariant=True)

if typing.TYPE_CHECKING:
    from robot.api import Token

    IRobotToken = Token


else:
    # We don't want to import robot in this case (just do it when type-checking).
    class IRobotToken(Protocol):
        pass


class INode(Protocol):
    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int

    def get_token(self, name: str) -> IRobotToken:
        pass


class ILibraryImportNode(INode, Protocol):
    name: str
    alias: Optional[str]


class IKeywordNode(INode, Protocol):
    name: str


class IResourceImportNode(INode, Protocol):
    name: str


class NodeInfo(Generic[Y]):
    stack: tuple
    node: Y

    __slots__ = ["stack", "node"]

    def __init__(self, stack, node):
        self.stack = stack
        self.node = node


TokenInfo = namedtuple("TokenInfo", "stack, node, token")


class KeywordUsageInfo:
    __slots__ = [
        "stack",
        "node",
        "token",
        "name",
        "is_argument_usage",
        "argument_usage_index",
    ]

    def __init__(
        self, stack, node, token, name, is_argument_usage=False, argument_usage_index=-1
    ):
        self.stack = stack
        self.node = node
        self.token = token
        self.name = name
        self.is_argument_usage = is_argument_usage
        self.argument_usage_index = argument_usage_index

    def __repr__(self):
        if self.is_argument_usage:
            return f"KeywordUsageInfo({self.name} (argument usage: {self.argument_usage_index}))"
        else:
            return f"KeywordUsageInfo({self.name})"

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
        pass

    def has_keyword_usage(self, normalized_keyword_name: str) -> bool:
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


class IRobotWorkspace(IWorkspace, Protocol):
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


class IKeywordDefinition(IDefinition, Protocol):

    keyword_found: IKeywordFound


def cast_to_keyword_definition(definition: IDefinition) -> Optional[IKeywordDefinition]:
    if hasattr(definition, "keyword_found"):
        return typing.cast(IKeywordDefinition, definition)
    return None


class IBaseCompletionContext(Protocol):
    @property
    def monitor(self) -> Optional[IMonitor]:
        pass

    @property
    def workspace(self) -> Optional[IRobotWorkspace]:
        pass

    @property
    def config(self) -> Optional[IConfig]:
        pass

    def check_cancelled(self) -> None:
        pass


class CompletionType(enum.Enum):
    regular = 1
    shell = 2


class ICompletionContext(Protocol):
    def __init__(
        self,
        doc,
        line=Sentinel.SENTINEL,
        col=Sentinel.SENTINEL,
        workspace=None,
        config=None,
        memo=None,
        monitor: IMonitor = NULL,
    ) -> None:
        """
        :param robocorp_ls_core.workspace.Document doc:
        :param int line:
        :param int col:
        :param RobotWorkspace workspace:
        :param robocorp_ls_core.config.Config config:
        :param _Memo memo:
        """

    def resolve_completion_item(
        self, data, completion_item: CompletionItemTypedDict, monaco: bool = False
    ) -> None:
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

    def get_ast_current_section(self) -> Any:
        """
        :rtype: robot.parsing.model.blocks.Section|NoneType
        """

    def get_section(self, section_name: str) -> Any:
        """
        :rtype: robot_constants.Section
        """

    def get_accepted_section_header_words(self) -> List[str]:
        pass

    def get_current_section_name(self) -> Optional[str]:
        pass

    def get_current_token(self) -> Optional[TokenInfo]:
        pass

    def get_all_variables(self) -> Tuple[NodeInfo, ...]:
        pass

    def get_current_variable(self, section=None) -> Optional[TokenInfo]:
        pass

    def get_resource_import_as_doc(self, resource_import) -> Optional[IRobotDocument]:
        pass

    def get_variable_import_as_doc(self, variables_import) -> Optional[IRobotDocument]:
        pass

    def get_current_keyword_definition(self) -> Optional[IKeywordDefinition]:
        pass

    def get_resource_imports_as_docs(
        self,
    ) -> Tuple[Tuple[IResourceImportNode, Optional[IRobotDocument]], ...]:
        pass

    def get_variable_imports_as_docs(self) -> Tuple[IRobotDocument, ...]:
        pass

    def get_imported_libraries(self) -> Tuple[ILibraryImportNode, ...]:
        pass

    def token_value_resolving_variables(self, token) -> str:
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


class IVariableFound(Protocol):
    """
    :ivar variable_name:
    :ivar variable_value:
    :ivar completion_context:
        This may be a new completion context, created when a new document is
        being analyzed (the variable was created for that completion context).
    :ivar source:
        Source where the variable was found.
    :ivar lineno:
        Line where it was found (0-based).
    """

    variable_name: str = ""
    variable_value: str = ""
    completion_context: Optional[ICompletionContext] = None

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
        pass

    def on_variable(self, variable_found: IVariableFound):
        pass


class EvaluatableExpressionTypedDict(TypedDict):
    range: RangeTypedDict
    expression: Optional[str]
