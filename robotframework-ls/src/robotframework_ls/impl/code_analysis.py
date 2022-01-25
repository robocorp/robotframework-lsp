from typing import Dict, Set

from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.ast_utils import MAX_ERRORS
from robotframework_ls.impl.protocols import (
    IKeywordFound,
    IKeywordCollector,
    ICompletionContext,
)


log = get_logger(__name__)


class _KeywordContainer(object):
    def __init__(self) -> None:
        self._name_to_keyword: Dict[str, IKeywordFound] = {}
        self._names_with_variables: Set[str] = set()

    def add_keyword(self, keyword_found: IKeywordFound) -> None:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        self._name_to_keyword[normalized_name] = keyword_found

        if "{" in normalized_name:
            self._names_with_variables.add(normalized_name)

    def contains_keyword(self, normalized_keyword_name: str):
        from robotframework_ls.impl.text_utilities import matches_robot_keyword

        if normalized_keyword_name in self._name_to_keyword:
            return True

        # We do not have an exact match, still, we need to check if we may
        # have a match in keywords that accept variables.
        for name in self._names_with_variables:
            if matches_robot_keyword(normalized_keyword_name, name):
                return True

        return False


class _AnalysisKeywordsCollector(object):
    def __init__(self, on_unresolved_library, on_unresolved_resource):
        self._keywords_container = _KeywordContainer()
        self._resource_name_to_keywords_container = {}
        self._library_name_to_keywords_container = {}
        self._on_unresolved_library = on_unresolved_library
        self._on_unresolved_resource = on_unresolved_resource

    def accepts(self, keyword_name):
        return True

    def on_keyword(self, keyword_found: IKeywordFound):
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        # Note: Even if something is imported 'WITH NAME', it's still added
        # to the global scope (there's just an additional reference with the
        # new name).
        self._keywords_container.add_keyword(keyword_found)
        library_name = keyword_found.library_name
        library_alias = keyword_found.library_alias
        resource_name = keyword_found.resource_name

        if library_name:
            if library_alias:
                name = normalize_robot_name(library_alias)
            else:
                name = normalize_robot_name(library_name)
            dct = self._library_name_to_keywords_container
        elif resource_name:
            name = normalize_robot_name(resource_name)
            dct = self._resource_name_to_keywords_container
        else:
            log.info(
                "No library name nor resource name for keyword: %s",
                keyword_found.keyword_name,
            )
            return

        keyword_container = dct.get(name)
        if keyword_container is None:
            keyword_container = dct[name] = _KeywordContainer()

        keyword_container.add_keyword(keyword_found)

    def contains_keyword(self, normalized_keyword_name):
        from robotframework_ls.impl import text_utilities

        if self._keywords_container.contains_keyword(normalized_keyword_name):
            return True

        # Note: the name could be something as `alias.keywordname` or
        # 'libraryname.keywordname`. In this case, we need to verify if there's
        # a library/alias with that specific name.
        for name, remainder in text_utilities.iter_dotted_names(
            normalized_keyword_name
        ):
            if not name or not remainder:
                continue
            containers = []
            keywords_container = self._resource_name_to_keywords_container.get(name)
            if keywords_container:
                containers.append(keywords_container)
            keywords_container = self._library_name_to_keywords_container.get(name)
            if keywords_container:
                containers.append(keywords_container)

            for keywords_container in containers:
                if keywords_container.contains_keyword(remainder):
                    return True

        return False

    def on_unresolved_library(
        self,
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        self._on_unresolved_library(
            completion_context,
            library_name,
            lineno,
            end_lineno,
            col_offset,
            end_col_offset,
        )

    def on_unresolved_resource(
        self,
        completion_context: ICompletionContext,
        resource_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        self._on_unresolved_resource(
            completion_context,
            resource_name,
            lineno,
            end_lineno,
            col_offset,
            end_col_offset,
        )

    def __typecheckself__(self) -> None:
        _: IKeywordCollector = check_implements(self)


def collect_analysis_errors(initial_completion_context):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_error_from_node
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.text_utilities import contains_variable_text

    errors = []

    def on_unresolved_library(
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        doc = completion_context.doc
        if doc and doc.uri == initial_completion_context.doc.uri:
            start = (lineno - 1, col_offset)
            end = (end_lineno - 1, end_col_offset)
            errors.append(
                ast_utils.Error(f"Unresolved library: {library_name}", start, end)
            )

    def on_unresolved_resource(
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        doc = completion_context.doc
        if doc and doc.uri == initial_completion_context.doc.uri:
            start = (lineno - 1, col_offset)
            end = (end_lineno - 1, end_col_offset)
            errors.append(
                ast_utils.Error(f"Unresolved resource: {library_name}", start, end)
            )

    collector = _AnalysisKeywordsCollector(
        on_unresolved_library, on_unresolved_resource
    )
    collect_keywords(initial_completion_context, collector)

    ast = initial_completion_context.get_ast()
    for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        initial_completion_context.check_cancelled()
        if contains_variable_text(keyword_usage_info.name):
            continue
        normalized_name = normalize_robot_name(keyword_usage_info.name)
        if not collector.contains_keyword(normalized_name):

            # There's not a direct match, but the library name may be builtin
            # into the keyword name, so, check if we have a match that way.

            node = keyword_usage_info.node
            error = create_error_from_node(
                node,
                "Undefined keyword: %s." % (keyword_usage_info.name,),
                tokens=[keyword_usage_info.token],
            )
            errors.append(error)
            if len(errors) >= MAX_ERRORS:
                # i.e.: Collect at most 100 errors
                break
    return errors
