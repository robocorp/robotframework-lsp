from collections import namedtuple
import os.path

from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    IKeywordFound,
    ICompletionContext,
    IKeywordCollector,
)
from robotframework_ls.impl.robot_specbuilder import KeywordArg
from typing import Tuple, Sequence, List, Dict, Optional


log = get_logger(__name__)


def _build_docs(keyword_name, args, docs, docs_format):

    if docs_format == "markdown":
        # Multi-line approach (it's a bit too big -- maybe as an option?)
        # if docs_format == "markdown":
        #     arg_docs = "  \n&nbsp;&nbsp;&nbsp;&nbsp;".join(
        #         ("**" + (x.replace("*", "\\*") + "**") for x in args)
        #     )
        #     return f"**{keyword_name}**  \n&nbsp;&nbsp;&nbsp;&nbsp;{arg_docs}\n\n{docs}"

        if args:
            escaped_args = (x.replace("*", "\\*") for x in args)
            arg_docs = f'({", ".join(escaped_args)})'

        else:
            arg_docs = ""
        return f"**{keyword_name}{arg_docs}**\n\n{docs}"
    else:
        if args:
            arg_docs = f'({", ".join(args)})'

        else:
            arg_docs = ""

        return f"{keyword_name}{arg_docs}\n\n{docs}"


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
        keyword_args: Sequence[KeywordArg],
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
    def keyword_args(self) -> Sequence[KeywordArg]:
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

    @property
    def docs_format(self):
        return "markdown"

    @property
    @instance_cache
    def docs(self) -> str:
        from robotframework_ls.impl import ast_utils

        docs = ast_utils.get_documentation(self._keyword_node)
        args = [x.original_arg for x in self.keyword_args]

        return _build_docs(self.keyword_name, args, docs, "markdown")

    @property
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
        library_doc,
        keyword_doc,
        keyword_name,
        keyword_args: Sequence[KeywordArg],
        completion_context,
        completion_item_kind,
        library_alias=None,
    ):

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
    def keyword_args(self) -> Sequence[KeywordArg]:
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

    @property
    @instance_cache
    def source(self):
        source = self._keyword_doc.source or self._library_doc.source
        return source

    @property
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

    @property
    @instance_cache
    def _docs_and_format(self) -> Tuple[str, str]:
        from robotframework_ls.impl.robot_specbuilder import docs_and_format

        docs, docs_format = docs_and_format(self._keyword_doc)
        if self.keyword_args:
            args = [x.original_arg for x in self.keyword_args]

            docs = _build_docs(self.keyword_name, args, docs, docs_format)

        return docs, docs_format

    @property
    @instance_cache
    def docs(self):
        docs, _docs_format = self._docs_and_format
        return docs

    @property
    @instance_cache
    def docs_format(self):
        _docs, docs_format = self._docs_and_format
        return docs_format

    def __typecheckself__(self) -> None:
        _: IKeywordFound = check_implements(self)


def _collect_completions_from_ast(
    ast, completion_context: ICompletionContext, collector
):
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import CompletionItemKind

    found = {}

    for keyword in ast_utils.iter_keywords(ast):
        completion_context.check_cancelled()
        keyword_name = keyword.node.name
        if collector.accepts(keyword_name):
            keyword_args = []
            for arg in ast_utils.iter_keyword_arguments_as_str(keyword.node):
                keyword_args.append(KeywordArg(arg))

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
    _collect_completions_from_ast(ast, completion_context, collector)


_LibInfo = namedtuple("_LibInfo", "name, alias, builtin, args, node")


def _collect_libraries_keywords(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords from libraries
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB
    from robocorp_ls_core.lsp import CompletionItemKind
    from robotframework_ls.impl import ast_utils

    libraries = completion_context.get_imported_libraries()

    # Note: using a dict(_LibInfo:bool) where only the keys are meaningful
    # because we want to keep the order and sets aren't ordered.
    library_infos = {}
    for name, alias, args, node in (
        (
            library.name,
            library.alias,
            ast_utils.get_library_arguments_serialized(library),
            library,
        )
        for library in libraries
    ):
        if name:
            lib_info = _LibInfo(
                completion_context.token_value_resolving_variables(name),
                alias,
                False,
                args,
                node,
            )

            library_infos[lib_info] = True

    library_infos[_LibInfo(BUILTIN_LIB, None, True, None, None)] = True
    libspec_manager = completion_context.workspace.libspec_manager

    for library_info in library_infos:
        completion_context.check_cancelled()
        if not completion_context.memo.complete_for_library(
            library_info.name, library_info.alias
        ):
            continue

        library_doc = libspec_manager.get_library_info(
            library_info.name,
            create=True,
            current_doc_uri=completion_context.doc.uri,
            builtin=library_info.builtin,
            args=library_info.args,
        )
        if library_doc is not None:
            #: :type keyword: KeywordDoc
            for keyword in library_doc.keywords:
                keyword_name = keyword.name
                if collector.accepts(keyword_name):

                    keyword_args = []
                    if keyword.args:
                        keyword_args = keyword.args

                    collector.on_keyword(
                        _KeywordFoundFromLibrary(
                            library_doc,
                            keyword,
                            keyword_name,
                            keyword_args,
                            completion_context,
                            CompletionItemKind.Method,
                            library_alias=library_info.alias,
                        )
                    )
        else:
            from robot.api import Token

            node = library_info.node
            node_name_tok = node.get_token(Token.NAME)
            if node_name_tok is not None:
                collector.on_unresolved_library(
                    completion_context,
                    node.name,
                    node_name_tok.lineno,
                    node_name_tok.lineno,
                    node_name_tok.col_offset,
                    node_name_tok.end_col_offset,
                )
            else:
                collector.on_unresolved_library(
                    completion_context,
                    library_info.name,
                    node.lineno,
                    node.end_lineno,
                    node.col_offset,
                    node.end_col_offset,
                )


def _collect_resource_imports_keywords(
    completion_context: ICompletionContext, collector: IKeywordCollector
):

    for node, resource_doc in completion_context.get_resource_imports_as_docs():
        if resource_doc is None:
            from robot.api import Token

            node_name_tok = node.get_token(Token.NAME)
            if node_name_tok is not None:
                collector.on_unresolved_resource(
                    completion_context,
                    node.name,
                    node_name_tok.lineno,
                    node_name_tok.lineno,
                    node_name_tok.col_offset,
                    node_name_tok.end_col_offset,
                )
            else:
                collector.on_unresolved_resource(
                    completion_context,
                    node.name,
                    node.lineno,
                    node.end_lineno,
                    node.col_offset,
                    node.end_col_offset,
                )
            continue
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_following_imports(new_ctx, collector)


def _collect_following_imports(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    completion_context.check_cancelled()
    if completion_context.memo.follow_import(completion_context.doc.uri):
        # i.e.: prevent collecting keywords for the same doc more than once.

        _collect_current_doc_keywords(completion_context, collector)

        _collect_resource_imports_keywords(completion_context, collector)

        _collect_libraries_keywords(completion_context, collector)


class _CollectKeywordNameToKeywordFound:
    def __init__(self) -> None:
        self.keyword_name_to_keyword_found: Dict[str, List[IKeywordFound]] = {}

    def accepts(self, keyword_name: str) -> bool:
        return True

    def on_keyword(self, keyword_found: IKeywordFound):
        lst = self.keyword_name_to_keyword_found.get(keyword_found.keyword_name)
        if lst is None:
            self.keyword_name_to_keyword_found[keyword_found.keyword_name] = lst = []
        lst.append(keyword_found)

    def on_unresolved_library(
        self,
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        pass

    def on_unresolved_resource(
        self,
        completion_context: ICompletionContext,
        resource_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
    ):
        pass

    def __typecheckself__(self) -> None:
        _: IKeywordCollector = check_implements(self)


def collect_keyword_name_to_keyword_found(
    completion_context: ICompletionContext,
) -> Dict[str, List[IKeywordFound]]:
    completion_context.memo.clear()
    collector = _CollectKeywordNameToKeywordFound()
    _collect_following_imports(completion_context, collector)
    return collector.keyword_name_to_keyword_found


def collect_keywords(
    completion_context: ICompletionContext, collector: IKeywordCollector
):
    """
    Collects all the keywords that are available to the given completion_context.
    """
    completion_context.memo.clear()
    _collect_following_imports(completion_context, collector)
