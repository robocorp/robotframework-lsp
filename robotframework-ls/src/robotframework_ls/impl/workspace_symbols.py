from typing import Optional, List
from robotframework_ls.impl.completion_context import BaseContext
from robocorp_ls_core.lsp import SymbolInformationTypedDict
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def workspace_symbols(
    query: Optional[str], context: BaseContext
) -> List[SymbolInformationTypedDict]:
    from robocorp_ls_core.lsp import SymbolKind
    from robotframework_ls.impl.libspec_manager import LibspecManager
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc
    from robocorp_ls_core import uris

    ret: List[SymbolInformationTypedDict] = []

    libspec_manager: LibspecManager = context.workspace.libspec_manager
    for library_name in libspec_manager.get_library_names():
        library_info: Optional[LibraryDoc] = libspec_manager.get_library_info(
            library_name, create=True
        )
        if library_info is not None:
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
                if lineno < 1:
                    log.info("Found lineno < 0 for: %s (in %s)", keyword, source)
                    continue

                lineno -= 1
                ret.append(
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

    return ret
