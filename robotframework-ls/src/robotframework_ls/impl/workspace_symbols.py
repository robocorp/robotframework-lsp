from typing import Optional, List, Set, Iterator
from robocorp_ls_core.lsp import (
    SymbolInformationTypedDict,
    MarkupContentTypedDict,
    MarkupKind,
)
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ISymbolsCache,
    IBaseCompletionContext,
    ILibraryDoc,
    IKeywordDoc,
    ISymbolKeywordInfo,
)
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS,
)
from robocorp_ls_core.options import USE_TIMEOUTS
from robotframework_ls.impl.protocols import ISymbolsJsonListEntry
import typing
from robotframework_ls.impl._symbols_cache import BaseSymbolsCache
from robocorp_ls_core.protocols import check_implements

log = get_logger(__name__)

WORKSPACE_SYMBOLS_FIRST_TIMEOUT = 10.0  # The first time it can take a bit longer
WORKSPACE_SYMBOLS_TIMEOUT = 1.0

if not USE_TIMEOUTS:
    WORKSPACE_SYMBOLS_FIRST_TIMEOUT = 999999.0
    WORKSPACE_SYMBOLS_TIMEOUT = 999999.0


def _add_to_ret(ret, symbols_cache: ISymbolsCache, query: Optional[str]):
    # Note that we could filter it here based on the passed query, but
    # this is not being done for now for simplicity (given that we'd need
    # to do a fuzzy matching close to what the client already does anyways).
    ret.extend(symbols_cache.get_json_list())


class _SymbolKeywordInfoFromKeywordDoc:

    _documentation: MarkupContentTypedDict

    __slots__ = ["name", "_keyword_doc", "_documentation"]

    def __init__(self, keyword_doc: IKeywordDoc):
        self.name = keyword_doc.name
        self._keyword_doc = keyword_doc

    def get_documentation(self) -> MarkupContentTypedDict:
        from robotframework_ls.impl.text_utilities import (
            build_keyword_docs_with_signature,
        )

        try:
            return self._documentation
        except AttributeError:
            from robotframework_ls.impl.robot_specbuilder import docs_and_format

            docs, docs_format = docs_and_format(self._keyword_doc)
            docs = build_keyword_docs_with_signature(
                self._keyword_doc.name,
                tuple(x.original_arg for x in self._keyword_doc.args),
                docs,
                docs_format,
            )

            self._documentation = {
                "kind": MarkupKind.Markdown,
                "value": docs,
            }

        return self._documentation

    def __typecheckself__(self) -> None:
        _: ISymbolKeywordInfo = check_implements(self)


class _SymbolsCacheForLibrary(BaseSymbolsCache):
    _cached_keyword_info: List[ISymbolKeywordInfo]

    def iter_keyword_info(self) -> Iterator[ISymbolKeywordInfo]:
        try:
            yield from iter(self._cached_keyword_info)
        except:
            cache: List[ISymbolKeywordInfo] = []

            library_info = self.get_library_info()
            if library_info is not None:
                for keyword_doc in library_info.keywords:
                    info = _SymbolKeywordInfoFromKeywordDoc(keyword_doc)
                    yield info
                    cache.append(info)

            self._cached_keyword_info = cache

    def __typecheckself__(self) -> None:
        _: ISymbolsCache = check_implements(self)


def _compute_symbols_from_library_info(
    library_name: str, library_info: ILibraryDoc
) -> ISymbolsCache:
    from robocorp_ls_core import uris
    from robocorp_ls_core.lsp import SymbolKind

    symbols: List[ISymbolsJsonListEntry] = []
    keyword: IKeywordDoc
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
    return _SymbolsCacheForLibrary(symbols, library_info, None, set(), None, None)


def iter_symbols_caches(
    query: Optional[str],
    context: IBaseCompletionContext,
    show_builtins: bool = True,
    force_all_docs_in_workspace: bool = False,
    timeout: Optional[float] = None,
    _called=[],
) -> Iterator[ISymbolsCache]:
    if timeout is not None:
        TIMEOUT = timeout
    else:
        if not _called:
            TIMEOUT = WORKSPACE_SYMBOLS_FIRST_TIMEOUT
            _called.append(True)
        else:
            TIMEOUT = WORKSPACE_SYMBOLS_TIMEOUT

    try:
        from robotframework_ls.impl.libspec_manager import LibspecManager
        from robotframework_ls.impl.robot_workspace import RobotWorkspace
        from robotframework_ls.impl.robot_constants import (
            BUILTIN_LIB,
            RESERVED_LIB,
        )

        workspace: Optional[RobotWorkspace] = typing.cast(
            Optional[RobotWorkspace], context.workspace
        )
        if not workspace:
            return

        found: Set[str] = set()
        symbols_cache: Optional[ISymbolsCache]

        config = context.config
        workspace_symbols_only_for_open_docs = False
        if config and not force_all_docs_in_workspace:
            workspace_symbols_only_for_open_docs = config.get_setting(
                OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS, bool, False
            )

        import time

        initial_time = time.time()

        workspace_indexer = workspace.workspace_indexer
        if workspace_indexer is None:
            # i.e.: this can happen if this is being asked on a server where we aren't indexing the workspace contents.
            log.critical(
                "Error: workspace.workspace_indexer is None in iter_symbols_caches (it seems that the wrong API is being used here)."
            )

        else:
            for _uri, symbols_cache in workspace_indexer.iter_uri_and_symbols_cache(
                only_for_open_docs=workspace_symbols_only_for_open_docs,
                initial_time=initial_time,
                timeout=TIMEOUT,
                context=context,
                found=found,
            ):
                if symbols_cache is not None:
                    yield symbols_cache

        libspec_manager: LibspecManager = workspace.libspec_manager
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
