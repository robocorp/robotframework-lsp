from typing import Optional, List, Set, Iterator
from robocorp_ls_core.lsp import SymbolInformationTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    IRobotDocument,
    ISymbolsCache,
    IBaseCompletionContext,
    ILibraryDoc,
)
import weakref
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS,
)
from robocorp_ls_core.options import USE_TIMEOUTS

log = get_logger(__name__)

WORKSPACE_SYMBOLS_FIRST_TIMEOUT = 6.0  # The first time it can take a bit longer
WORKSPACE_SYMBOLS_TIMEOUT = 1.0

if not USE_TIMEOUTS:
    WORKSPACE_SYMBOLS_FIRST_TIMEOUT = 999999.0
    WORKSPACE_SYMBOLS_TIMEOUT = 999999.0


class SymbolsCache:
    _library_info: "Optional[weakref.ReferenceType[ILibraryDoc]]"
    _doc: "Optional[weakref.ReferenceType[IRobotDocument]]"

    def __init__(
        self,
        json_list,
        library_info: Optional[ILibraryDoc],
        doc: Optional[IRobotDocument],
    ):
        if library_info is not None:
            self._library_info = weakref.ref(library_info)
        else:
            self._library_info = None

        if doc is not None:
            self._doc = weakref.ref(doc)
        else:
            self._doc = None

        self._json_list = json_list

    def get_json_list(self) -> list:
        return self._json_list

    def get_library_info(self) -> Optional[ILibraryDoc]:
        w = self._library_info
        if w is None:
            return None
        return w()

    def get_doc(self) -> Optional[IRobotDocument]:
        w = self._doc
        if w is None:
            return None
        return w()


def _add_to_ret(ret, symbols_cache: ISymbolsCache, query: Optional[str]):
    # Note that we could filter it here based on the passed query, but
    # this is not being done for now for simplicity (given that we'd need
    # to do a fuzzy matching close to what the client already does anyways).
    ret.extend(symbols_cache.get_json_list())


def _compute_symbols_from_ast(doc: IRobotDocument) -> ISymbolsCache:
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import SymbolKind

    ast = doc.get_ast()
    symbols = []
    uri = doc.uri

    for keyword_node_info in ast_utils.iter_keywords(ast):
        symbols.append(
            {
                "name": keyword_node_info.node.name,
                "kind": SymbolKind.Class,
                "location": {
                    "uri": uri,
                    "range": {
                        "start": {
                            "line": keyword_node_info.node.lineno - 1,
                            "character": keyword_node_info.node.col_offset,
                        },
                        "end": {
                            "line": keyword_node_info.node.end_lineno - 1,
                            "character": keyword_node_info.node.end_col_offset,
                        },
                    },
                },
            }
        )
    return SymbolsCache(symbols, None, doc)


def _compute_symbols_from_library_info(library_name, library_info) -> SymbolsCache:
    from robocorp_ls_core.lsp import SymbolKind
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from robocorp_ls_core import uris

    symbols = []
    keyword: KeywordDoc
    for keyword in library_info.keywords:
        source = keyword.source
        if not source:
            source = library_info.source

        if not source:
            log.info("Found no source for: %s", library_info)
            continue

        uri = uris.from_fs_path(source)
        lineno = keyword.lineno
        if lineno < 0:
            # This happens for some Reserved.py keywords (which should
            # not be shown.
            continue

        lineno -= 1
        symbols.append(
            {
                "name": keyword.name,
                "kind": SymbolKind.Method,
                "location": {
                    "uri": uri,
                    "range": {
                        "start": {"line": lineno, "character": 0},
                        "end": {"line": lineno, "character": 0},
                    },
                },
                "containerName": library_name,
            }
        )
    return SymbolsCache(symbols, library_info, None)


def iter_symbols_caches(
    query: Optional[str],
    context: IBaseCompletionContext,
    show_builtins: bool = True,
    called=[],
) -> Iterator[ISymbolsCache]:
    if not called:
        TIMEOUT = WORKSPACE_SYMBOLS_FIRST_TIMEOUT
        called.append(True)
    else:
        TIMEOUT = WORKSPACE_SYMBOLS_TIMEOUT

    try:
        from robotframework_ls.impl.libspec_manager import LibspecManager
        from robotframework_ls.impl.protocols import IRobotWorkspace
        from typing import cast
        from robotframework_ls.impl.robot_constants import (
            STDLIBS,
            BUILTIN_LIB,
            RESERVED_LIB,
        )

        workspace: Optional[IRobotWorkspace] = context.workspace
        if not workspace:
            return
        libspec_manager: LibspecManager = workspace.libspec_manager

        library_name_and_current_doc: Set[tuple] = set()
        for name in STDLIBS:
            if name == RESERVED_LIB:
                continue
            if not show_builtins and name == BUILTIN_LIB:
                continue
            library_name_and_current_doc.add((name, None))

        found = set()
        symbols_cache: Optional[ISymbolsCache]

        config = context.config
        workspace_symbols_only_for_open_docs = False
        if config:
            workspace_symbols_only_for_open_docs = config.get_setting(
                OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS, bool, False
            )

        import time

        initial_time = time.time()

        if workspace_symbols_only_for_open_docs:

            def iter_in():
                for doc_uri in workspace.get_open_docs_uris():
                    yield doc_uri

        else:

            def iter_in():
                for uri in workspace.iter_all_doc_uris_in_workspace(
                    (".robot", ".resource")
                ):
                    yield uri

        for uri in iter_in():
            if not uri:
                continue

            context.check_cancelled()

            if time.time() - initial_time > TIMEOUT:
                log.info(
                    "Timed out gathering information from workspace symbols (only partial information was collected). Consider enabling the 'robot.workspaceSymbolsOnlyForOpenDocs' setting."
                )
                break

            doc = cast(
                Optional[IRobotDocument],
                workspace.get_document(uri, accept_from_file=True),
            )
            if doc is not None:
                if uri in found:
                    continue
                found.add(uri)
                symbols_cache = doc.symbols_cache
                if symbols_cache is None:
                    symbols_cache = _compute_symbols_from_ast(doc)
                doc.symbols_cache = symbols_cache
                yield symbols_cache

        already_checked = set()
        library_info: ILibraryDoc
        # I.e.: just iterate over pre-created (don't create any here as it may be slow...
        # let code analysis or some background thread do that).
        for _internal_lib_info in libspec_manager.iter_lib_info():
            library_info = _internal_lib_info.library_doc
            library_name = library_info.name
            if library_name == RESERVED_LIB:
                continue
            if not show_builtins and library_name == BUILTIN_LIB:
                continue

            library_id = (library_info.name, library_info.source)
            if library_id in already_checked:
                continue
            already_checked.add(library_id)

            context.check_cancelled()

            if time.time() - initial_time > TIMEOUT:
                log.info(
                    "Timed out gathering information from workspace symbols (only partial information was collected). Consider enabling the 'robot.workspaceSymbolsOnlyForOpenDocs' setting."
                )
                break

            if library_info is not None:
                if library_info.source is not None:
                    if library_info.source in found:
                        continue
                    found.add(library_info.source)

                symbols_cache = library_info.symbols_cache
                if symbols_cache is None:
                    symbols_cache = _compute_symbols_from_library_info(
                        library_name, library_info
                    )

                yield symbols_cache
                library_info.symbols_cache = symbols_cache
    except Exception:
        log.exception()
        raise


def workspace_symbols(
    query: Optional[str], context: IBaseCompletionContext
) -> List[SymbolInformationTypedDict]:
    ret: List[SymbolInformationTypedDict] = []

    for symbols_cache in iter_symbols_caches(query, context):
        _add_to_ret(ret, symbols_cache, query)

    return ret
