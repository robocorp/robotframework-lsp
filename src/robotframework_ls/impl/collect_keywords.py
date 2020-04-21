import os.path
from robotframework_ls.robotframework_log import get_logger
from robotframework_ls import cache

log = get_logger(__name__)


class _KeywordFoundFromAst(object):

    __slots__ = [
        "_module_ast",
        "_keyword_node",
        "keyword_name",
        "keyword_args",
        "completion_context",
        "completion_item_kind",
        "__instance_cache__",
    ]

    def __init__(
        self,
        module_ast,
        keyword_node,
        keyword_name,
        keyword_args,
        completion_context,
        completion_item_kind,
    ):
        self._module_ast = module_ast
        self._keyword_node = keyword_node

        self.keyword_name = keyword_name
        self.keyword_args = keyword_args
        self.completion_context = completion_context
        self.completion_item_kind = completion_item_kind

    @property
    def docs_format(self):
        return "markdown"

    @property
    @cache.instance_cache
    def docs(self):
        from robotframework_ls.impl import ast_utils

        return ast_utils.get_documentation(self._keyword_node)

    @property
    @cache.instance_cache
    def source(self):
        from robotframework_ls import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self._keyword_node.lineno - 1

    @property
    def end_lineno(self):
        return self._keyword_node.end_lineno - 1

    @property
    def col_offset(self):
        return self._keyword_node.col_offset

    @property
    def end_col_offset(self):
        return self._keyword_node.end_col_offset


class _KeywordFoundFromLibrary(object):

    __slots__ = [
        "_library_doc",
        "_keyword_doc",
        "keyword_name",
        "keyword_args",
        "completion_context",
        "completion_item_kind",
        "__instance_cache__",
    ]

    def __init__(
        self,
        library_doc,
        keyword_doc,
        keyword_name,
        keyword_args,
        completion_context,
        completion_item_kind,
    ):

        self._library_doc = library_doc
        self._keyword_doc = keyword_doc
        self.keyword_name = keyword_name
        self.keyword_args = keyword_args

        self.completion_context = completion_context
        self.completion_item_kind = completion_item_kind

    @property
    @cache.instance_cache
    def source(self):
        source = self._keyword_doc.source or self._library_doc.source
        if source:
            if not os.path.isabs(source):
                source = self._make_absolute(source)
        return source

    @cache.instance_cache
    def _make_absolute(self, source):
        dirname = os.path.dirname(self._library_doc.filename)
        return os.path.abspath(os.path.join(dirname, source))

    @property
    @cache.instance_cache
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
    @cache.instance_cache
    def _docs_and_format(self):
        from robotframework_ls.impl.robot_specbuilder import docs_and_format

        return docs_and_format(self._keyword_doc)

    @property
    @cache.instance_cache
    def docs(self):
        docs, _docs_format = self._docs_and_format
        return docs

    @property
    @cache.instance_cache
    def docs_format(self):
        _docs, docs_format = self._docs_and_format
        return docs_format


def _collect_completions_from_ast(ast, completion_context, collector):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.lsp import CompletionItemKind

    for keyword in ast_utils.iter_keywords(ast):
        keyword_name = keyword.node.name
        if collector.accepts(keyword_name):
            keyword_args = []
            for arg in ast_utils.iter_keyword_arguments_as_str(keyword.node):
                keyword_args.append(arg)

            collector.on_keyword(
                _KeywordFoundFromAst(
                    ast,
                    keyword.node,
                    keyword_name,
                    keyword_args,
                    completion_context,
                    CompletionItemKind.Function,
                )
            )


def _collect_current_doc_keywords(completion_context, collector):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, collector)


def _collect_libraries_keywords(completion_context, collector):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords from libraries
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB
    from robotframework_ls.lsp import CompletionItemKind

    libraries = completion_context.get_imported_libraries()
    library_names = set(library.name for library in libraries)
    library_names.add(BUILTIN_LIB)
    libspec_manager = completion_context.workspace.libspec_manager

    for library_name in library_names:
        if not completion_context.memo.complete_for_library(library_name):
            continue

        library_doc = libspec_manager.get_library_info(library_name, create=True)
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
                        )
                    )


def _collect_resource_imports_keywords(completion_context, collector):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls import uris

    # Get keywords from resources
    resource_imports = completion_context.get_resource_imports()
    for resource_import in resource_imports:
        for token in resource_import.tokens:
            if token.type == token.NAME:
                parts = []
                for v in token.tokenize_variables():
                    if v.type == v.NAME:
                        parts.append(str(v))

                    elif v.type == v.VARIABLE:
                        # Resolve variable from config
                        v = str(v)
                        if v.startswith("${") and v.endswith("}"):
                            v = v[2:-1]
                            parts.append(completion_context.convert_robot_variable(v))
                        else:
                            log.info("Cannot resolve variable: %s", v)

                resource_path = "".join(parts)
                if not os.path.isabs(resource_path):
                    # It's a relative resource, resolve its location based on the
                    # current file.
                    resource_path = os.path.join(
                        os.path.dirname(completion_context.doc.path), resource_path
                    )

                ws = completion_context.workspace
                if not os.path.exists(resource_path):
                    log.info("Resource not found: %s", resource_path)
                    continue

                doc_uri = uris.from_fs_path(resource_path)

                resource_doc = ws.get_document(doc_uri, create=False)
                if resource_doc is None:
                    resource_doc = ws.create_untracked_document(doc_uri)

                new_ctx = completion_context.create_copy(resource_doc)
                _collect_following_imports(new_ctx, collector)


def _collect_following_imports(completion_context, collector):
    if completion_context.memo.follow_import(completion_context.doc.uri):
        # i.e.: prevent collecting keywords for the same doc more than once.

        _collect_current_doc_keywords(completion_context, collector)

        _collect_resource_imports_keywords(completion_context, collector)

        _collect_libraries_keywords(completion_context, collector)


class IKeywordFound(object):
    """
    :ivar keyword_name:
    :ivar keyword_args:
    :ivar docs:
    :ivar docs_format:
    :ivar completion_context:
        This may be a new completion context, created when a new document is
        being analyzed (the keyword was created for that completion context).
        For libraries the initial completion context is passed.
    :ivar completion_item_kind:
    :ivar source:
        Source where the keyword was found.
    :ivar lineno:
        Line where it was found (0-based). 
    """

    keyword_name = ""
    keyword_args = []
    docs = ""
    docs_format = ""
    completion_context = None
    completion_item_kind = -1
    source = ""
    lineno = -1
    end_lineno = -1
    col_offset = -1
    end_col_offset = -1


class ICollector(object):
    def accepts(self, keyword_name):
        """
        :param keyword_name:
            The name of the keyword to be accepted or not.
        :return bool:
            If the return is True, on_keyword(...) is called (otherwise it's not
            called).
        """

    def on_keyword(self, keyword_found):
        """
        :param IKeywordFound keyword_found:
        """


def collect_keywords(completion_context, collector):
    """
    Collects all the keywords that are available to the given completion_context.
    
    :param CompletionContext completion_context:
    :param ICollector collector:
    """
    _collect_following_imports(completion_context, collector)
