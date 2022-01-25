from typing import List, Optional, Dict, Iterator

from robocorp_ls_core.lsp import LocationTypedDict, RangeTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    IKeywordFound,
    IVariablesCollector,
    IVariableFound,
)
import typing
import os
from robocorp_ls_core.protocols import check_implements


log = get_logger(__name__)


def matches_source(s1: str, s2: str) -> bool:
    if s1 == s2:
        return True

    return os.path.normcase(os.path.normpath(s1)) == os.path.normcase(
        os.path.normpath(s2)
    )


class _VariableDefinitionsCollector(object):
    def __init__(self, robot_string_matcher):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        self.robot_string_matcher: RobotStringMatcher = robot_string_matcher
        self.matches: List[IVariableFound] = []

    def accepts(self, variable_name):
        return self.robot_string_matcher.is_same_variable_name(variable_name)

    def on_variable(self, variable_found: IVariableFound):
        self.matches.append(variable_found)

    def __typecheckself__(self) -> None:
        _: IVariablesCollector = check_implements(self)


def iter_variable_references_in_doc(
    completion_context: ICompletionContext,
    doc: IRobotDocument,
    normalized_name: str,
) -> Iterator[RangeTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_range_from_token
    from robotframework_ls.impl.variable_completions import collect_variables

    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robocorp_ls_core.lsp import PositionTypedDict

    robot_string_matcher = RobotStringMatcher(normalized_name)

    ast = doc.get_ast()
    if ast is not None:
        for node_info in ast_utils.iter_variable_references(ast):
            completion_context.check_cancelled()
            if robot_string_matcher.is_same_variable_name(node_info.token.value):
                yield create_range_from_token(node_info.token)

        collector = _VariableDefinitionsCollector(robot_string_matcher)
        collect_variables(completion_context, collector, only_current_doc=True)

        variable: IVariableFound
        for variable in collector.matches:
            start: PositionTypedDict = {
                "line": variable.lineno,
                "character": variable.col_offset,
            }
            end: PositionTypedDict = {
                "line": variable.lineno,
                "character": variable.end_col_offset,
            }
            code_lens_range: RangeTypedDict = {"start": start, "end": end}
            yield code_lens_range


def iter_keyword_references_in_doc(
    completion_context: ICompletionContext,
    doc: IRobotDocument,
    normalized_name: str,
    keyword_found: Optional[IKeywordFound],
) -> Iterator[RangeTypedDict]:
    """
    :param keyword_found: if given, we'll match if the definition actually
    maps to the proper place (if not given, we'll just match based on the name
    without verifying if the definition is the same).
    """
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.find_definition import find_definition
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    ast = doc.get_ast()
    if ast is not None:
        # Dict with normalized name -> whether it was found or not previously.
        found_in_this_doc: Dict[str, bool] = {}

        # Ok, we have the document, now, load the usages.
        for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
            ast, collect_args_as_keywords=True
        ):
            completion_context.check_cancelled()
            keword_name_possibly_dotted = keyword_usage_info.name
            found_dot_in_usage = "." in keword_name_possibly_dotted
            if found_dot_in_usage:
                keword_name_not_dotted = keword_name_possibly_dotted.split(".")[-1]
            else:
                keword_name_not_dotted = keword_name_possibly_dotted

            if normalize_robot_name(keword_name_not_dotted) == normalized_name:
                found_once_in_this_doc = found_in_this_doc.get(
                    keword_name_possibly_dotted
                )
                token = keyword_usage_info.token

                line = token.lineno - 1

                if keyword_found is not None:
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
                            found = matches_source(
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
                        len(keword_name_possibly_dotted) - len(keword_name_not_dotted)
                    )
                    end_col_offset = token.end_col_offset
                else:
                    col_offset = token.col_offset
                    end_col_offset = token.end_col_offset

                # Ok, we found it, let's add it to the result.
                yield {
                    "start": {
                        "line": line,
                        "character": col_offset,
                    },
                    "end": {
                        "line": line,
                        "character": end_col_offset,
                    },
                }


def references(
    completion_context: ICompletionContext, include_declaration: bool
) -> List[LocationTypedDict]:
    from robocorp_ls_core import uris
    from robotframework_ls.impl.text_utilities import normalize_robot_name

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

                ref_range: RangeTypedDict
                for ref_range in iter_keyword_references_in_doc(
                    completion_context, doc, normalized_name, keyword_found
                ):
                    ret.append({"uri": doc.uri, "range": ref_range})
    return ret
