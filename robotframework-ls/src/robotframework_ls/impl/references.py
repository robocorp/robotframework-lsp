from typing import List, Optional, Dict

from robocorp_ls_core.lsp import LocationTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import ICompletionContext, IRobotDocument
import typing
import os


log = get_logger(__name__)


def _matches_source(s1, s2):
    if s1 == s2:
        return True

    return os.path.normcase(os.path.normpath(s1)) == os.path.normcase(
        os.path.normpath(s2)
    )


def references(
    completion_context: ICompletionContext, include_declaration: bool
) -> List[LocationTypedDict]:
    from robotframework_ls.impl.protocols import IKeywordFound
    from robocorp_ls_core import uris
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.find_definition import find_definition
    from robotframework_ls.impl.completion_context import CompletionContext

    ret: List[LocationTypedDict] = []
    current_keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if current_keyword_definition_and_usage_info is not None:
        completion_context.monitor.check_cancelled()
        keyword_definition, _usage_info = current_keyword_definition_and_usage_info

        keyword_found: IKeywordFound = keyword_definition.keyword_found

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        # Ok, we have the keyword definition, now, we must actually look for the
        # references...
        if include_declaration:
            ret.append(
                {
                    "uri": uris.from_fs_path(keyword_found.source),
                    "range": {
                        "start": {
                            "line": keyword_found.lineno,
                            "character": keyword_found.col_offset,
                        },
                        "end": {
                            "line": keyword_found.end_lineno,
                            "character": keyword_found.end_col_offset,
                        },
                    },
                }
            )

        from robotframework_ls.impl.workspace_symbols import iter_symbols_caches

        for symbols_cache in iter_symbols_caches(
            None, completion_context, force_all_docs_in_workspace=True, timeout=999999
        ):
            completion_context.check_cancelled()
            if symbols_cache.has_keyword_usage(normalized_name):
                doc: Optional[IRobotDocument] = symbols_cache.get_doc()
                if doc is None:
                    uri = symbols_cache.get_uri()
                    if uri is None:
                        continue

                    doc = typing.cast(
                        Optional[IRobotDocument],
                        completion_context.workspace.get_document(
                            doc_uri=uri, accept_from_file=True
                        ),
                    )

                    if doc is None:
                        log.debug(
                            "Unable to load document for getting references with uri: %s",
                            uri,
                        )
                        continue

                ast = doc.get_ast()
                if ast is None:
                    continue

                # Dict with normalized name -> whether it was found or not previously.
                found_in_this_doc: Dict[str, bool] = {}

                # Ok, we have the document, now, load the usages.
                for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
                    ast, collect_args_as_keywords=True
                ):
                    keword_name_possibly_dotted = keyword_usage_info.name
                    found_dot_in_usage = "." in keword_name_possibly_dotted
                    if found_dot_in_usage:
                        keword_name_not_dotted = keword_name_possibly_dotted.split(".")[
                            -1
                        ]
                    else:
                        keword_name_not_dotted = keword_name_possibly_dotted

                    if normalize_robot_name(keword_name_not_dotted) == normalized_name:
                        found_once_in_this_doc = found_in_this_doc.get(
                            keword_name_possibly_dotted
                        )
                        token = keyword_usage_info.token

                        line = token.lineno - 1
                        if found_once_in_this_doc is None:
                            # Verify if it's actually the same one (not one defined in
                            # a different place with the same name).

                            new_ctx = CompletionContext(
                                doc,
                                line,
                                token.col_offset,
                                workspace=completion_context.workspace,
                                config=completion_context.config,
                                monitor=completion_context.monitor,
                            )
                            definitions = find_definition(new_ctx)
                            for definition in definitions:
                                found = _matches_source(
                                    definition.source, keyword_found.source
                                )

                                if found:
                                    found_once_in_this_doc = found_in_this_doc[
                                        keword_name_possibly_dotted
                                    ] = True
                                    break
                            else:
                                found_once_in_this_doc = found_in_this_doc[
                                    keword_name_possibly_dotted
                                ] = False
                                continue

                        if not found_once_in_this_doc:
                            continue

                        token = keyword_usage_info.token
                        if found_dot_in_usage:
                            # We need to create a new token because we just want to match the name part.
                            col_offset = token.col_offset + (
                                len(keword_name_possibly_dotted)
                                - len(keword_name_not_dotted)
                            )
                            end_col_offset = token.end_col_offset
                        else:
                            col_offset = token.col_offset
                            end_col_offset = token.end_col_offset

                        # Ok, we found it, let's add it to the result.
                        ret.append(
                            {
                                "uri": doc.uri,
                                "range": {
                                    "start": {
                                        "line": line,
                                        "character": col_offset,
                                    },
                                    "end": {
                                        "line": line,
                                        "character": end_col_offset,
                                    },
                                },
                            }
                        )
    return ret
