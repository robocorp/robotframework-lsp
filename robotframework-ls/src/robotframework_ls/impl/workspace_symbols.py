from typing import Optional, List, Set
from robotframework_ls.impl.completion_context import BaseContext
from robocorp_ls_core.lsp import SymbolInformationTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import IRobotDocument

log = get_logger(__name__)


def add_to_ret(ret, symbols_cache, query: Optional[str]):
    # Note that we could filter it here based on the passed query, but
    # this is not being done for now for simplicity (given that we'd need
    # to do a fuzzy matching close to what the client already does anyways).
    ret.extend(symbols_cache)


def _compute_symbols_from_ast(doc: IRobotDocument):
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
    return symbols


def _compute_symbols_from_library_info(library_name, library_info):
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
    return symbols


def workspace_symbols(
    query: Optional[str], context: BaseContext
) -> List[SymbolInformationTypedDict]:
    from robotframework_ls.impl.libspec_manager import LibspecManager
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robocorp_ls_core import uris
    from robotframework_ls.impl.protocols import IRobotWorkspace
    from pathlib import Path
    from typing import cast
    from robotframework_ls.impl import ast_utils

    ret: List[SymbolInformationTypedDict] = []
    workspace: IRobotWorkspace = context.workspace
    libspec_manager: LibspecManager = workspace.libspec_manager

    folder_paths = sorted(set(workspace.get_folder_paths()))
    library_names: Set[str] = set()

    for folder_path in folder_paths:
        for path in Path(folder_path).glob("**/*"):
            if path.name.lower().endswith((".robot", ".resource", ".txt")):
                doc = cast(
                    Optional[IRobotDocument],
                    workspace.get_document(
                        uris.from_fs_path(str(path)), accept_from_file=True
                    ),
                )
                if doc is not None:
                    symbols_cache = doc.symbols_cache
                    if symbols_cache is None:
                        symbols_cache = _compute_symbols_from_ast(doc)
                    doc.symbols_cache = symbols_cache
                    add_to_ret(ret, symbols_cache, query)

                    ast = doc.get_ast()
                    if ast:
                        for library_import in ast_utils.iter_library_imports(ast):
                            library_names.add(library_import.node.name)

    library_names.update(libspec_manager.get_library_names())

    for library_name in library_names:
        library_info: Optional[LibraryDoc] = libspec_manager.get_library_info(
            library_name, create=True
        )
        if library_info is not None:
            symbols_cache = library_info.symbols_cache
            if symbols_cache is None:
                symbols_cache = _compute_symbols_from_library_info(
                    library_name, library_info
                )

            library_info.symbols_cache = symbols_cache
            add_to_ret(ret, symbols_cache, query)

    return ret
