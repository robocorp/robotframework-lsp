import os.path

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    IKeywordFound,
    ICompletionContext,
    IKeywordCollector,
    IKeywordArg,
    LibraryDependencyInfo,
    AbstractKeywordCollector,
    INode,
)
from typing import Sequence, List, Dict, Optional, Iterator, Any
from robotframework_ls.impl.text_utilities import build_keyword_docs_with_signature
from robocorp_ls_core.lsp import MarkupContentTypedDict, MarkupKind


log = get_logger(__name__)


class _KeywordFoundFromAst(object):
    __slots__ = [
        "_module_ast",
        "_keyword_node",
        "_keyword_name",
        "_keyword_args",
        "completion_context",
        "completion_item_kind",
        "_name_token",
        "__instance_cache__",
    ]

    def __init__(
        self,
        module_ast,
        keyword_node,
        keyword_name,
        keyword_args: Sequence[IKeywordArg],
        completion_context,
        completion_item_kind,
    ):
        from robot.api import Token

        self._module_ast = module_ast
        self._keyword_node = keyword_node

        self._name_token = keyword_node.header.get_token(Token.KEYWORD_NAME)

        self._keyword_name = keyword_name
        self._keyword_args = keyword_args
        self.completion_context = completion_context
        self.completion_item_kind = completion_item_kind

    @property
    def keyword_name(self):
        return self._keyword_name

    @property
    def keyword_ast(self) -> Optional[INode]:
        return self._keyword_node

    @property
    def keyword_args(self) -> Sequence[IKeywordArg]:
        return self._keyword_args

    @property
    def library_alias(self):
        return None

    @property
    def library_name(self):
        return None

    @property
    def resource_name(self):
        from robocorp_ls_core import uris

        uri = self.completion_context.doc.uri
        return os.path.splitext(os.path.basename(uris.to_fs_path(uri)))[0]

    def compute_docs_without_signature(self) -> MarkupContentTypedDict:
        return {
            "kind": MarkupKind.Markdown,
            "value": self._docs_without_signature(),
        }

    def compute_docs_with_signature(self) -> MarkupContentTypedDict:
        docs = build_keyword_docs_with_signature(
            self.keyword_name,
            tuple(x.original_arg for x in self.keyword_args),
            self._docs_without_signature(),
            "markdown",
        )
        return {
            "kind": MarkupKind.Markdown,
            "value": docs,
        }

    @instance_cache
    def _docs_without_signature(self) -> str:
        from robotframework_ls.impl import ast_utils

        return ast_utils.get_documentation_as_markdown(self._keyword_node)

    @instance_cache
    def is_deprecated(self) -> bool:
        from robotframework_ls.impl import ast_utils

        return ast_utils.is_deprecated(self._keyword_node)

    @property  # type: ignore
    @instance_cache
    def source(self) -> str:
        from robocorp_ls_core import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self._name_token.lineno - 1

    @property
    def end_lineno(self):
        return self._name_token.lineno - 1

    @property
    def col_offset(self):
        return self._name_token.col_offset

    @property
    def end_col_offset(self):
        return self._name_token.end_col_offset

    @property
    def scope_lineno(self) -> Optional[int]:
        return self._keyword_node.lineno - 1

    @property
    def scope_end_lineno(self) -> Optional[int]:
        return self._keyword_node.end_lineno - 1

    @property
    def scope_col_offset(self) -> Optional[int]:
        return self._keyword_node.col_offset

    @property
    def scope_end_col_offset(self) -> Optional[int]:
        return self._keyword_node.end_col_offset

    def __typecheckself__(self) -> None:
        _: IKeywordFound = check_implements(self)


class _KeywordFoundFromLibrary(object):
    __slots__ = [
        "_lib_deprecated",
        "_library_doc",
        "_library_alias",
        "_keyword_doc",
        "_keyword_name",
        "_keyword_args",
        "completion_context",
        "completion_item_kind",
        "__instance_cache__",
    ]

    def __init__(
        self,
        lib_deprecated,
        library_doc,
        keyword_doc,
        keyword_name,
        keyword_args: Sequence[IKeywordArg],
        completion_context,
        completion_item_kind,
        library_alias=None,
    ):
        self._lib_deprecated = lib_deprecated
        self._library_doc = library_doc
        self._keyword_doc = keyword_doc
        self._keyword_name = keyword_name
        self._keyword_args = keyword_args

        self.completion_context = completion_context
        self.completion_item_kind = completion_item_kind
        self._library_alias = library_alias

    @property
    def keyword_name(self):
        return self._keyword_name

    @property
    def keyword_ast(self) -> Optional[INode]:
        return None

    @property
    def keyword_args(self) -> Sequence[IKeywordArg]:
        return self._keyword_args

    @property
    def library_alias(self):
        return self._library_alias

    @property
    def library_name(self):
        return self._library_doc.name

    @property
    def resource_name(self):
        return None

    @instance_cache
    def is_deprecated(self):
        if self._lib_deprecated:
            return self._lib_deprecated
        from robotframework_ls.impl import text_utilities

        return text_utilities.has_deprecated_text(self._keyword_doc.doc)

    @property  # type: ignore
    @instance_cache
    def source(self):
        source = self._keyword_doc.source or self._library_doc.source
        return source

    @property  # type: ignore
    @instance_cache
    def lineno(self):
        return self._keyword_doc.lineno - 1  # i.e.: make 0-based.

    @property
    def end_lineno(self):
        return self.lineno

    @property
    def col_offset(self):
        return 0

    @property
    def end_col_offset(self):
        return 0

    @property
    def scope_lineno(self) -> Optional[int]:
        return self.lineno

    @property
    def scope_end_lineno(self) -> Optional[int]:
        return self.end_lineno

    @property
    def scope_col_offset(self) -> Optional[int]:
        return self.col_offset

    @property
    def scope_end_col_offset(self) -> Optional[int]:
        return self.end_col_offset

    def compute_docs_without_signature(self) -> MarkupContentTypedDict:
        from robotframework_ls.impl.robot_specbuilder import docs_and_format

        docs, docs_format = docs_and_format(self._keyword_doc)

        return {"kind": docs_format, "value": docs}

    def compute_docs_with_signature(self) -> MarkupContentTypedDict:
        from robotframework_ls.impl.robot_specbuilder import docs_and_format

        docs, docs_format = docs_and_format(self._keyword_doc)
        docs = build_keyword_docs_with_signature(
            self.keyword_name,
            tuple(x.original_arg for x in self.keyword_args),
            docs,
            docs_format,
        )

        return {
            "kind": docs_format,
            "value": docs,
        }

    def __typecheckself__(self) -> None:
        _: IKeywordFound = check_implements(self)


def collect_keywords_from_ast(
    ast, completion_context: ICompletionContext, collector: IKeywordCollector
):
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import CompletionItemKind

    found = {}

    for keyword in ast_utils.iter_keywords(ast):
        completion_context.check_cancelled()
        keyword_name = keyword.node.name
        if collector.accepts(keyword_name):
            keyword_args = list(ast_utils.iter_keyword_arguments_as_kwarg(keyword.node))

            found[keyword_name] = _KeywordFoundFromAst(
                ast,
                keyword.node,
                keyword_name,
                keyword_args,
                completion_context,
                CompletionItemKind.Function,
            )

    # We notify afterwards because if multiple definitions of the same
    # keyword are found, we just want to report the last one (as is the
    # case for the interactive console).
    for keyword_found in found.values():
        collector.on_keyword(keyword_found)


def _collect_current_doc_keywords(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    collect_keywords_from_ast(ast, completion_context, collector)


def _collect_libraries_keywords(
    completion_context: ICompletionContext,
    library_infos: Iterator[LibraryDependencyInfo],
    collector: IKeywordCollector,
    memo: Dict[Any, Any],
):
    from robotframework_ls.impl.libspec_manager import LibspecManager
    from robotframework_ls.impl.protocols import ILibraryDocOrError
    from robotframework_ls.impl import text_utilities

    # Get keywords from libraries
    from robocorp_ls_core.lsp import CompletionItemKind

    libspec_manager: LibspecManager = completion_context.workspace.libspec_manager
    tracing = completion_context.tracing

    for library_info in library_infos:
        if tracing:
            log.debug(
                "Collected library info: name: %s - alias: %s",
                library_info.name,
                library_info.alias,
            )

        completion_context.check_cancelled()

        library_doc_or_error: ILibraryDocOrError = (
            libspec_manager.get_library_doc_or_error(
                library_info.name,
                create=True,
                completion_context=completion_context,
                builtin=library_info.builtin,
                args=library_info.args,
            )
        )
        library_doc = library_doc_or_error.library_doc

        if library_doc is not None:
            key: Any = library_doc.source
            if not key:
                key = library_doc
            key = (key, library_info.alias)

            visited = memo.get(key, False)
            if visited:
                continue
            else:
                memo[key] = True

            doc = library_doc.doc
            lib_deprecated = doc and text_utilities.has_deprecated_text(doc)

            #: :type keyword: KeywordDoc
            for keyword in library_doc.keywords:
                keyword_name = keyword.name
                if collector.accepts(keyword_name):
                    if tracing:
                        log.debug(
                            "Accepted keyword name: %s (libname: %s, libalias: %s)",
                            keyword_name,
                            library_info.name,
                            library_info.alias,
                        )

                    keyword_args: Sequence[IKeywordArg] = ()
                    if keyword.args:
                        keyword_args = keyword.args

                    collector.on_keyword(
                        _KeywordFoundFromLibrary(
                            lib_deprecated,
                            library_doc,
                            keyword,
                            keyword_name,
                            keyword_args,
                            completion_context,
                            CompletionItemKind.Method,
                            library_alias=library_info.alias,
                        )
                    )

            collector.on_resolved_library(
                completion_context, library_info.node, library_doc
            )
        else:
            from robot.api import Token

            error_msg = library_doc_or_error.error
            node = library_info.node
            if node:
                if error_msg:
                    error_msg = f"\nError generating libspec:\n{error_msg}"

                node_name_tok = node.get_token(Token.NAME)

                if node_name_tok is not None:
                    (
                        value,
                        token_errors,
                    ) = completion_context.token_value_and_unresolved_resolving_variables(
                        node_name_tok
                    )
                    if token_errors:
                        for token_error, error_msg in token_errors:
                            collector.on_unresolved_library(
                                completion_context,
                                node.name,
                                token_error.lineno,
                                token_error.lineno,
                                token_error.col_offset,
                                token_error.end_col_offset,
                                error_msg,
                                value,
                            )
                    else:
                        collector.on_unresolved_library(
                            completion_context,
                            node.name,
                            node_name_tok.lineno,
                            node_name_tok.lineno,
                            node_name_tok.col_offset,
                            node_name_tok.end_col_offset,
                            error_msg,
                            value,
                        )
                else:
                    collector.on_unresolved_library(
                        completion_context,
                        library_info.name,
                        node.lineno,
                        node.end_lineno,
                        node.col_offset,
                        node.end_col_offset,
                        error_msg,
                        "",
                    )


def _collect_from_context(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    dependency_graph = completion_context.collect_dependency_graph()

    root_doc = dependency_graph.get_root_doc()
    assert root_doc.uri == completion_context.doc.uri
    _collect_current_doc_keywords(completion_context, collector)

    completion_context.check_cancelled()
    memo: Dict[Any, Any] = {}
    _collect_libraries_keywords(
        completion_context,
        dependency_graph.iter_libraries(completion_context.doc.uri),
        collector,
        memo,
    )

    for node, resource_doc in dependency_graph.iter_all_resource_imports_with_docs():
        completion_context.check_cancelled()

        if resource_doc is None:
            # Note that 'None' documents will only be given for the
            # initial context (so, it's ok to use `completion_context`
            # in this case).
            from robot.api import Token

            node_name_tok = node.get_token(Token.NAME)
            if node_name_tok is not None:
                (
                    value,
                    token_errors,
                ) = completion_context.token_value_and_unresolved_resolving_variables(
                    node_name_tok
                )

                if token_errors:
                    for token_error, error_msg in token_errors:
                        collector.on_unresolved_resource(
                            completion_context,
                            node.name,
                            token_error.lineno,
                            token_error.lineno,
                            token_error.col_offset,
                            token_error.end_col_offset,
                            error_msg,
                            value,
                        )

                else:
                    collector.on_unresolved_resource(
                        completion_context,
                        node.name,
                        node_name_tok.lineno,
                        node_name_tok.lineno,
                        node_name_tok.col_offset,
                        node_name_tok.end_col_offset,
                        None,
                        value,
                    )
            else:
                collector.on_unresolved_resource(
                    completion_context,
                    node.name,
                    node.lineno,
                    node.end_lineno,
                    node.col_offset,
                    node.end_col_offset,
                    None,
                    "",
                )
            continue
        completion_context.check_cancelled()
        new_ctx = completion_context.create_copy(resource_doc)

        _collect_current_doc_keywords(new_ctx, collector)
        _collect_libraries_keywords(
            new_ctx,
            dependency_graph.iter_libraries(resource_doc.uri),
            collector,
            memo,
        )


class _CollectKeywordNameToKeywordFound(AbstractKeywordCollector):
    def __init__(self) -> None:
        self.keyword_name_to_keyword_found: Dict[str, List[IKeywordFound]] = {}

    def accepts(self, keyword_name: str) -> bool:
        return True

    def on_keyword(self, keyword_found: IKeywordFound):
        lst = self.keyword_name_to_keyword_found.get(keyword_found.keyword_name)
        if lst is None:
            self.keyword_name_to_keyword_found[keyword_found.keyword_name] = lst = []
        lst.append(keyword_found)

    def __typecheckself__(self) -> None:
        _: IKeywordCollector = check_implements(self)


def collect_keyword_name_to_keyword_found(
    completion_context: ICompletionContext,
) -> Dict[str, List[IKeywordFound]]:
    collector = _CollectKeywordNameToKeywordFound()
    _collect_from_context(completion_context, collector)
    return collector.keyword_name_to_keyword_found


def collect_keywords(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    """
    Collects all the keywords that are available to the given completion_context.
    """
    _collect_from_context(completion_context, collector)
