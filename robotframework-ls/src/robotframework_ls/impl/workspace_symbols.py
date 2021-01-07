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

log = get_logger(__name__)


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
    query: Optional[str], context: IBaseCompletionContext, show_builtins: bool = True
) -> Iterator[ISymbolsCache]:
    try:
        from robotframework_ls.impl.libspec_manager import LibspecManager
        from robotframework_ls.impl.protocols import IRobotWorkspace
        from typing import cast
        from robotframework_ls.impl import ast_utils
        from robotframework_ls.impl.robot_constants import STDLIBS, BUILTIN_LIB

        workspace: Optional[IRobotWorkspace] = context.workspace
        if not workspace:
            return
        libspec_manager: LibspecManager = workspace.libspec_manager

        library_name_and_current_doc: Set[tuple] = set()
        for name in STDLIBS:
            if not show_builtins and name == BUILTIN_LIB:
                continue
            library_name_and_current_doc.add((name, None))

        found = set()
        symbols_cache: Optional[ISymbolsCache]
        for uri in workspace.iter_all_doc_uris_in_workspace(
            (".robot", ".resource", ".txt")
        ):
            if not uri:
                continue

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

                ast = doc.get_ast()
                if ast:
                    for library_import in ast_utils.iter_library_imports(ast):
                        target_filename = libspec_manager.get_library_target_filename(
                            library_import.node.name, doc.uri
                        )

                        if not target_filename:
                            library_name_and_current_doc.add(
                                (library_import.node.name, None)
                            )
                        else:
                            library_name_and_current_doc.add(
                                (library_import.node.name, doc.uri)
                            )
        for library_name, current_doc_uri in library_name_and_current_doc:
            library_info: Optional[ILibraryDoc] = libspec_manager.get_library_info(
                library_name, create=True, current_doc_uri=current_doc_uri
            )
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
    except:
        log.exception()
        raise


def workspace_symbols(
    query: Optional[str], context: IBaseCompletionContext
) -> List[SymbolInformationTypedDict]:
    ret: List[SymbolInformationTypedDict] = []

    for symbols_cache in iter_symbols_caches(query, context):
        _add_to_ret(ret, symbols_cache, query)

    return ret
