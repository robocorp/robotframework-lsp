import threading
from typing import Optional, Any, Set, List, Dict, Iterable, Tuple, Iterator
import typing
import weakref

from robocorp_ls_core import uris
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.cache import instance_cache
from robocorp_ls_core.lsp import (
    TextDocumentContentChangeEvent,
    TextDocumentItem,
    MarkupContentTypedDict,
    MarkupKind,
)
from robocorp_ls_core.protocols import (
    check_implements,
    IWorkspaceFolder,
    IEndPoint,
    ITestInfoFromSymbolsCacheTypedDict,
    ITestInfoFromUriTypedDict,
    IDocument,
    IConfig,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.watchdog_wrapper import IFSObserver
from robocorp_ls_core.workspace import Workspace, Document
from robotframework_ls.constants import NULL
from robotframework_ls.impl._symbols_cache import BaseSymbolsCache
from robotframework_ls.impl.protocols import (
    IRobotWorkspace,
    IRobotDocument,
    IBaseCompletionContext,
    ISymbolsCache,
    ISymbolsJsonListEntry,
    ICompletionContext,
    IKeywordNode,
    ISymbolKeywordInfo,
    ICompletionContextWorkspaceCaches,
    IOnDependencyChanged,
    AbstractVariablesCollector,
    IVariableFound,
)
from robotframework_ls.impl.robot_constants import ROBOT_FILE_EXTENSIONS


log = get_logger(__name__)


class _KeywordInfo:
    _documentation: MarkupContentTypedDict

    __slots__ = ["_node", "name", "_documentation"]

    def __init__(self, node: IKeywordNode):
        self._node = node
        self.name = node.name

    def get_documentation(self) -> MarkupContentTypedDict:
        from robotframework_ls.impl import ast_utils
        from robotframework_ls.impl.text_utilities import (
            build_keyword_docs_with_signature,
        )

        try:
            return self._documentation
        except AttributeError:
            docs = ast_utils.get_documentation_as_markdown(self._node)
            args = tuple(ast_utils.iter_keyword_arguments_as_str(self._node))

            docs = build_keyword_docs_with_signature(self.name, args, docs, "markdown")

            self._documentation = {
                "kind": MarkupKind.Markdown,
                "value": docs,
            }

        return self._documentation

    def __typecheckself__(self) -> None:
        _: ISymbolKeywordInfo = check_implements(self)


class _SymbolsCacheForAST(BaseSymbolsCache):
    _cached_keyword_info: List[ISymbolKeywordInfo]

    def __init__(self, *args, **kwargs):
        keywords = kwargs.pop("keywords")
        self._keywords: List[IKeywordNode] = keywords
        super(_SymbolsCacheForAST, self).__init__(*args, **kwargs)

    def iter_keyword_info(self) -> Iterator[ISymbolKeywordInfo]:
        try:
            yield from iter(self._cached_keyword_info)
        except:
            cache: List[ISymbolKeywordInfo] = []
            for k in self._keywords:
                keyword_info = _KeywordInfo(k)
                yield keyword_info
                cache.append(keyword_info)
            self._cached_keyword_info = cache

    def __typecheckself__(self) -> None:
        _: ISymbolsCache = check_implements(self)


def _compute_symbols_from_ast(completion_context: ICompletionContext) -> ISymbolsCache:
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import SymbolKind
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.code_lens import list_tests
    from robotframework_ls.impl.variable_completions import (
        collect_current_doc_global_variables,
    )
    from robotframework_ls.impl import text_utilities

    doc = completion_context.doc

    ast = completion_context.get_ast()
    symbols: List[ISymbolsJsonListEntry] = []
    uri = doc.uri

    keywords: List[IKeywordNode] = []
    for keyword_node_info in ast_utils.iter_keywords(ast):
        keywords.append(keyword_node_info.node)
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
                "containerName": doc.path,
            }
        )

    keywords_used: Set[str] = set()
    for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        normalized = normalize_robot_name(keyword_usage_info.name)
        keywords_used.add(normalized)

        for name, remainder in text_utilities.iter_dotted_names(
            normalize_robot_name(keyword_usage_info.name)
        ):
            if not name or not remainder:
                continue
            keywords_used.add(remainder)

    test_info = list_tests(completion_context)
    test_info_for_cache: List[ITestInfoFromSymbolsCacheTypedDict] = [
        {"name": x["name"], "range": x["range"]} for x in test_info
    ]

    global_variables_collector = _GlobalVariablesCollector()
    collect_current_doc_global_variables(completion_context, global_variables_collector)

    variable_references: Set[str] = set()
    for variable_reference in ast_utils.iter_variable_references(ast):
        v = variable_reference.token.value
        if v:
            variable_references.add(normalize_robot_name(v))

    return _SymbolsCacheForAST(
        symbols,
        None,
        doc,
        keywords_used,
        uri=uri,
        test_info=test_info_for_cache,
        keywords=keywords,
        global_variables_defined=global_variables_collector.global_variables_defined,
        variable_references=variable_references,
    )


class _GlobalVariablesCollector(AbstractVariablesCollector):
    def __init__(self):
        self.global_variables_defined: Set[str] = set()

    def accepts(self, variable_name: str) -> bool:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        self.global_variables_defined.add(normalize_robot_name(variable_name))
        return False

    def on_variable(self, variable_found: IVariableFound):
        pass


class _ReindexInfo(object):
    def __init__(self):
        self.uris_to_iter: Set[str] = set()
        self.full_reindex: bool = False
        self.finished_collection = threading.Event()


class _ReindexManager(object):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._disposed = False

        self._reindex_info = _ReindexInfo()
        self._reindex_event = threading.Event()

        # i.e.: start with a full reindex.
        self._reindex_info.full_reindex = True
        self._reindex_event.set()

    def request_uri_collection(self, doc_uri: str) -> _ReindexInfo:
        with self._lock:
            if not self._disposed:
                self._reindex_info.uris_to_iter.add(doc_uri)

            self._reindex_event.set()
            return self._reindex_info

    # This isn't ideal because we don't process file removals as we should...
    # def request_directory_collection(self, directory):
    #     with self._lock:
    #         if not self._disposed:
    #             try:
    #                 for entry in os.scandir(directory):
    #                     if entry.path.endswith((".robot", ".resource")):
    #                         self._reindex_info.uris_to_iter.add(
    #                             uris.from_fs_path(entry.path)
    #                         )
    #             except:
    #                 # Directory removed: request full collection
    #                 self._reindex_info.full_reindex = True
    #
    #         self._reindex_event.set()
    #         return self._reindex_info

    def request_full_collection(self) -> _ReindexInfo:
        with self._lock:
            if not self._disposed:
                self._reindex_info.full_reindex = True

            self._reindex_event.set()
            return self._reindex_info

    def wait_for_info_to_reindex(self) -> _ReindexInfo:
        self._reindex_event.wait()
        with self._lock:
            if self._disposed:
                return self._reindex_info

            self._reindex_event.clear()
            ret = self._reindex_info
            self._reindex_info = _ReindexInfo()
            return ret

    def dispose(self):
        with self._lock:
            self._disposed = True
            self._reindex_info.finished_collection.set()

            self._reindex_info = _ReindexInfo()
            self._reindex_info.finished_collection.set()

            self._reindex_event.set()


class WorkspaceIndexer(object):
    def __init__(
        self,
        robot_workspace,
        endpoint: Optional[IEndPoint],
        collect_tests: bool = False,
    ) -> None:
        from robotframework_ls.impl._symbols_cache import SymbolsCacheReverseIndex

        self._robot_workspace = weakref.ref(robot_workspace)
        robot_workspace.on_file_changed.register(self._on_file_changed)
        self._endpoint = endpoint
        self._collect_tests = collect_tests
        self._clear_caches = threading.Event()
        self._reindex_manager = _ReindexManager()
        self._disposed = threading.Event()
        self.symbols_cache_reverse_index = SymbolsCacheReverseIndex()

        if collect_tests:
            assert endpoint is not None
        t = threading.Thread(target=self._on_thread)
        self._cached: Dict[str, Any] = {}
        t.daemon = True
        t.start()

    def _on_file_changed(self, filename: str):
        # with open("x:/temp/rara.txt", "a+") as stream:
        #     stream.write("%s\n" % filename)

        if filename and filename.endswith(ROBOT_FILE_EXTENSIONS):
            uri = uris.from_fs_path(filename)
            self._reindex_manager.request_uri_collection(uri)
            self.symbols_cache_reverse_index.notify_uri_changed(uri)

    def wait_for_full_test_collection(self):
        assert (
            self._collect_tests
        ), "Cannot wait for first test collection if not collecting tests."

        self._clear_caches.set()
        reindex_info = self._reindex_manager.request_full_collection()
        reindex_info.finished_collection.wait()

        return True

    def _on_thread(self) -> None:
        try:
            self._on_thread_internal()
        except:
            log.exception("Error in workpace indexer.")

    def _on_thread_internal(self) -> None:
        if not self._collect_tests:
            for _uri, symbols_cache in self.iter_uri_and_symbols_cache():
                # Do a single collection at startup, afterwards only
                # collect again on demand.
                pass
        else:
            endpoint = self._endpoint
            assert endpoint
            while True:
                reindex_info = self._reindex_manager.wait_for_info_to_reindex()

                if self._disposed.is_set():
                    reindex_info.finished_collection.set()
                    return

                try:
                    if self._clear_caches.is_set() or reindex_info.full_reindex:
                        # If clear caches is set, we need to force the notifications.
                        force_notify = self._clear_caches.is_set()
                        self._clear_caches.clear()

                        old_cached = self._cached
                        new_cached = {}

                        test_info_lst: List[ITestInfoFromSymbolsCacheTypedDict]
                        for uri, symbols_cache in self.iter_uri_and_symbols_cache():
                            if symbols_cache is None:
                                test_info_lst = []
                            else:
                                lst = symbols_cache.get_test_info()
                                if lst is None:
                                    test_info_lst = []
                                else:
                                    test_info_lst = lst

                            if uri:
                                test_info_for_uri: ITestInfoFromUriTypedDict = {
                                    "uri": uri,
                                    "testInfo": test_info_lst,
                                }
                                new_cached[uri] = test_info_lst
                                if (
                                    old_cached.pop(uri, None) != test_info_lst
                                    or force_notify
                                ):
                                    endpoint.notify(
                                        "$/testsCollected",
                                        test_info_for_uri,
                                    )

                        for uri in old_cached.keys():
                            endpoint.notify(
                                "$/testsCollected",
                                {"uri": uri, "testInfo": []},
                            )
                        self._cached = new_cached
                    else:
                        # In this case we won't notify about old keys removed
                        # because they weren't found (although if uris_to_iter
                        # has removed uris, we'll still do the right thing).
                        cached = self._cached

                        uris_to_iter = reindex_info.uris_to_iter
                        for uri, symbols_cache in self.iter_uri_and_symbols_cache(
                            uris_to_iter=uris_to_iter
                        ):
                            if symbols_cache is None:
                                test_info_lst = []
                            else:
                                lst = symbols_cache.get_test_info()
                                if lst is None:
                                    test_info_lst = []
                                else:
                                    test_info_lst = lst

                            if uri:
                                test_info_for_uri = {
                                    "uri": uri,
                                    "testInfo": test_info_lst,
                                }
                                if cached.get(uri) != test_info_lst:
                                    cached[uri] = test_info_lst
                                    endpoint.notify(
                                        "$/testsCollected",
                                        test_info_for_uri,
                                    )
                finally:
                    reindex_info.finished_collection.set()

    def dispose(self):
        self._disposed.set()
        self._reindex_manager.dispose()
        self.symbols_cache_reverse_index.dispose()

    def on_updated_document(self, doc_uri: str):
        self._reindex_manager.request_uri_collection(doc_uri)
        self.symbols_cache_reverse_index.notify_uri_changed(doc_uri)

    def on_updated_folders(self):
        self._reindex_manager.request_full_collection()
        self.symbols_cache_reverse_index.request_full_reindex()

    def iter_uri_and_symbols_cache(
        self,
        only_for_open_docs=False,
        initial_time: Optional[float] = None,
        timeout: Optional[float] = None,
        context: Optional[IBaseCompletionContext] = None,
        found: Optional[Set[str]] = None,
        uris_to_iter: Optional[Set[str]] = None,
    ) -> Iterable[Tuple[str, Optional[ISymbolsCache]]]:
        from typing import cast
        import time

        if not found:
            found = set()

        if initial_time is None:
            initial_time = time.time()

        if timeout is None:
            timeout = 99999999

        workspace = self._robot_workspace()
        if not workspace:
            log.critical("self._robot_workspace already collected in WorkspaceIndexer.")
            return

        if uris_to_iter is not None:

            def iter_in():
                yield from iter(uris_to_iter)

        else:
            if only_for_open_docs:

                def iter_in():
                    for doc_uri in workspace.get_open_docs_uris():
                        yield doc_uri

            else:

                def iter_in():
                    doc_uris = set()
                    for doc_uri in workspace.get_open_docs_uris():
                        doc_uris.add(doc_uri)
                        yield doc_uri

                    for uri in workspace.iter_all_doc_uris_in_workspace(
                        ROBOT_FILE_EXTENSIONS
                    ):
                        if uri not in doc_uris:
                            yield uri

        for uri in iter_in():
            if not uri:
                continue

            if context is not None:
                context.check_cancelled()

            if time.time() - initial_time > timeout:
                log.info(
                    "Timed out gathering information from workspace symbols (only partial information was collected). Consider enabling the 'robot.workspaceSymbolsOnlyForOpenDocs' setting."
                )
                break

            if uri in found:
                continue
            found.add(uri)

            doc = cast(
                Optional[IRobotDocument],
                workspace.get_document(uri, accept_from_file=True),
            )
            if doc is None:
                yield uri, None  # i.e.: No longer there...
                continue

            # Note that this can be accessed in multiple threads... We let it
            # compute at the same time but only one will be saved in the end
            # (which means we'll spend some more cpu cycles but we shouldn't
            # have any bad behavior due to it).
            symbols_cache = doc.symbols_cache
            if symbols_cache is None:
                from robotframework_ls.impl.completion_context import (
                    CompletionContext,
                )

                if context is not None:
                    ctx = CompletionContext(
                        doc,
                        monitor=context.monitor,
                        config=context.config,
                        workspace=workspace,
                    )
                else:
                    ctx = CompletionContext(
                        doc,
                        workspace=workspace,
                    )
                symbols_cache = _compute_symbols_from_ast(ctx)
            doc.symbols_cache = symbols_cache
            yield uri, symbols_cache


class RobotWorkspace(Workspace):
    def __init__(
        self,
        root_uri,
        fs_observer: IFSObserver,
        workspace_folders=None,
        libspec_manager=NULL,
        generate_ast=True,
        index_workspace=False,
        collect_tests=False,
        endpoint: Optional[IEndPoint] = None,
        on_dependency_changed: Optional[IOnDependencyChanged] = None,
    ):
        from robotframework_ls.impl.completion_context_workspace_caches import (
            CompletionContextWorkspaceCaches,
        )

        self.libspec_manager = libspec_manager

        # It needs to be set to None in the initialization (while we setup folders).
        self.workspace_indexer: Optional[WorkspaceIndexer] = None
        self.completion_context_workspace_caches: ICompletionContextWorkspaceCaches = (
            CompletionContextWorkspaceCaches(on_dependency_changed)
        )

        Workspace.__init__(
            self, root_uri, fs_observer, workspace_folders=workspace_folders
        )
        self._generate_ast = generate_ast
        self._lock_setup_workspace_indexer = threading.Lock()
        if collect_tests:
            assert endpoint is not None
            assert (
                index_workspace
            ), "Can only collect tests when the workspace indexing is setup too."

        if index_workspace:
            self.workspace_indexer = WorkspaceIndexer(
                self, endpoint, collect_tests=collect_tests
            )
        else:
            self.workspace_indexer = None

        self.on_file_changed.register(
            self.completion_context_workspace_caches.on_file_changed
        )

    def setup_workspace_indexer(self):
        with self._lock_setup_workspace_indexer:
            assert self.workspace_indexer is None
            self.workspace_indexer = WorkspaceIndexer(self, None, collect_tests=False)

    @overrides(Workspace.put_document)
    def put_document(self, text_document: TextDocumentItem) -> IDocument:
        doc = typing.cast(IRobotDocument, Workspace.put_document(self, text_document))
        self.completion_context_workspace_caches.on_updated_document(doc.uri, doc)
        if self.workspace_indexer is not None:
            self.workspace_indexer.on_updated_document(doc.uri)
        return doc

    @overrides(Workspace.update_document)
    def update_document(
        self, text_doc: TextDocumentItem, change: TextDocumentContentChangeEvent
    ) -> IDocument:
        doc = typing.cast(
            IRobotDocument, Workspace.update_document(self, text_doc, change)
        )
        self.completion_context_workspace_caches.on_updated_document(doc.uri, doc)
        if self.workspace_indexer is not None:
            self.workspace_indexer.on_updated_document(doc.uri)
        return doc

    @overrides(Workspace.remove_document)
    def remove_document(self, uri: str):
        doc = Workspace.remove_document(self, uri)
        self.completion_context_workspace_caches.on_updated_document(uri, None)
        if self.workspace_indexer is not None:
            self.workspace_indexer.on_updated_document(uri)
        return doc

    @overrides(Workspace.add_folder)
    def add_folder(self, folder: IWorkspaceFolder):
        Workspace.add_folder(self, folder)
        self.libspec_manager.add_workspace_folder(folder.uri)
        self.completion_context_workspace_caches.clear_caches()
        if self.workspace_indexer is not None:
            self.workspace_indexer.on_updated_folders()

    @overrides(Workspace.remove_folder)
    def remove_folder(self, folder_uri):
        Workspace.remove_folder(self, folder_uri)
        self.libspec_manager.remove_workspace_folder(folder_uri)
        self.completion_context_workspace_caches.clear_caches()
        if self.workspace_indexer is not None:
            self.workspace_indexer.on_updated_folders()

    @overrides(Workspace.on_changed_config)
    def on_changed_config(self, config: IConfig):
        Workspace.on_changed_config(self, config)
        self.completion_context_workspace_caches.clear_caches()

    @overrides(Workspace.dispose)
    def dispose(self):
        Workspace.dispose(self)
        self.completion_context_workspace_caches.dispose()
        indexer = self.workspace_indexer
        if indexer is not None:
            indexer.dispose()

    @overrides(Workspace._create_document)
    def _create_document(
        self, doc_uri, source=None, version=None, force_load_source=False
    ):
        return RobotDocument(
            doc_uri,
            source,
            version,
            generate_ast=self._generate_ast,
            mutate_thread=self._main_thread,
            force_load_source=force_load_source,
        )

    def __typecheckself__(self) -> None:
        _: IRobotWorkspace = check_implements(self)


class RobotDocument(Document):
    TYPE_TEST_CASE = "test_case"
    TYPE_INIT = "init"
    TYPE_RESOURCE = "resource"

    def __init__(
        self,
        uri,
        source=None,
        version=None,
        generate_ast=True,
        *,
        mutate_thread=None,
        force_load_source=False,
    ):
        Document.__init__(
            self,
            uri,
            source=source,
            version=version,
            mutate_thread=mutate_thread,
            force_load_source=force_load_source,
        )

        self._generate_ast = generate_ast
        self._ast = None
        self.symbols_cache = None

    @overrides(Document._clear_caches)
    def _clear_caches(self):
        Document._clear_caches(self)
        self._symbols_cache = None
        self.get_ast.cache_clear(self)  # noqa (clear the instance_cache).
        self.get_python_ast.cache_clear(self)  # noqa (clear the instance_cache).
        self.get_yaml_contents.cache_clear(self)  # noqa (clear the instance_cache).

    def get_type(self):
        path = self.path
        if not path:
            log.info("RobotDocument path empty.")
            return self.TYPE_TEST_CASE

        import os.path

        basename = os.path.basename(path)
        if basename.startswith("__init__"):
            return self.TYPE_INIT

        if basename.endswith(".resource"):
            return self.TYPE_RESOURCE

        return self.TYPE_TEST_CASE

    @instance_cache
    def get_ast(self):
        if not self._generate_ast:
            raise AssertionError(
                "The AST can only be accessed in the RobotFrameworkServerApi, not in the RobotFrameworkLanguageServer."
            )

        return self.generate_ast_uncached()

    def generate_ast_uncached(self) -> None:
        from robot.api import get_model, get_resource_model, get_init_model
        from robotframework_ls.impl.robot_localization import (
            get_global_localization_info,
        )
        from robotframework_ls.impl import ast_utils
        from robotframework_ls.impl.robot_version import robot_version_supports_language
        from robotframework_ls.impl.robot_localization import LocalizationInfo

        try:
            source: str = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            source = ""

        language_codes: List[str] = []
        try:
            kwargs: Dict[str, Any] = {}

            if robot_version_supports_language():
                try:
                    # Input localization
                    localization_info = get_global_localization_info()
                    from robot.api import Languages

                    languages = Languages()
                    for code in localization_info.language_codes:
                        languages.add_language(code)

                    kwargs["lang"] = languages
                except Exception:
                    log.exception(
                        "Error: Unable to use expected language API in this version of Robot Framework."
                    )

            t = self.get_type()
            if t == self.TYPE_TEST_CASE:
                ast = get_model(source, **kwargs)

            elif t == self.TYPE_RESOURCE:
                ast = get_resource_model(source, **kwargs)

            elif t == self.TYPE_INIT:
                ast = get_init_model(source, **kwargs)

            else:
                log.critical("Unrecognized section: %s", t)
                ast = get_model(source, **kwargs)

            # Output localization
            if robot_version_supports_language():
                language_codes.extend(getattr(ast, "languages", ()))

            localization_info = LocalizationInfo(tuple(language_codes))

            ast.source = self.path
            ast_utils.set_localization_info_in_model(ast, localization_info)
            return ast
        except:
            log.exception(f"Error parsing {self.uri}")
            # Note: we always want to return a valid AST here (the
            # AST itself should have the error).
            ast = get_model(f"*** Unable to parse: {self.uri} ***")

            localization_info = LocalizationInfo(tuple(language_codes))
            ast_utils.set_localization_info_in_model(ast, localization_info)
            ast.source = self.path
            return ast

    @instance_cache
    def get_python_ast(self):
        if not self._generate_ast:
            raise AssertionError(
                "The AST can only be accessed in the RobotFrameworkServerApi, not in the RobotFrameworkLanguageServer."
            )

        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            return None

        try:
            import ast as ast_module

            return ast_module.parse(source)
        except:
            log.critical(f"Error parsing python file: {self.uri}")
            return None

    @instance_cache
    def get_yaml_contents(self) -> Optional[Any]:
        try:
            source = self.source
        except:
            log.exception("Error getting source for: %s" % (self.uri,))
            return None

        try:
            from robocorp_ls_core import yaml_wrapper
            from io import StringIO

            s = StringIO()
            s.write(source)
            s.seek(0)
            return yaml_wrapper.load(s)
        except:
            log.critical(f"Error parsing yaml file: {self.uri}")
            return None

    def __typecheckself__(self) -> None:
        _: IRobotDocument = check_implements(self)
