from typing import Iterator, Tuple, Optional, Deque, Dict, Sequence, List, Set

from robocorp_ls_core.ordered_set import OrderedSet
from robotframework_ls.impl.protocols import (
    ICompletionContextDependencyGraph,
    LibraryDependencyInfo,
    ICompletionContext,
    IResourceImportNode,
    IRobotDocument,
    ICompletionContextWorkspaceCaches,
    IVariableImportNode,
)
from robotframework_ls.impl.robot_constants import BUILTIN_LIB
from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core import uris
import os
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class _Memo(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self._followed_imports_variables = {}
        self._followed_imports = {}
        self._completed_libraries = {}

    def follow_import(self, uri: str) -> bool:
        if uri not in self._followed_imports:
            self._followed_imports[uri] = True
            return True

        return False

    def follow_import_variables(self, uri: str) -> bool:
        if uri not in self._followed_imports_variables:
            self._followed_imports_variables[uri] = True
            return True

        return False

    def complete_for_library(self, library_name: str, alias: Optional[str]) -> bool:
        key = (library_name, alias)
        if key not in self._completed_libraries:
            self._completed_libraries[key] = True
            return True

        return False


class CompletionContextDependencyGraph:
    """
    This class is used to map dependencies from a given document

    i.e.: Imports / Resources / Variables
    """

    # Called as: on_before_cache_dependency_graph(ICompletionContextDependencyGraph)
    on_before_cache_dependency_graph = Callback()

    def __init__(self, root_doc: IRobotDocument):
        self._root_doc: IRobotDocument = root_doc
        self._doc_uri_to_library_infos: Dict[
            str, OrderedSet[LibraryDependencyInfo]
        ] = {}
        self._doc_uri_to_resource_imports: Dict[
            str, Sequence[Tuple[IResourceImportNode, Optional[IRobotDocument]]]
        ] = {}
        self._doc_uri_to_variable_imports: Dict[
            str, Sequence[Tuple[IVariableImportNode, Optional[IRobotDocument]]]
        ] = {}

        self._invalidate_on_uri_changes: Set[str] = set()
        self._invalidate_on_basename_no_ext_changes: Set[str] = set()

    def invalidate_on_basename_change(self, name):
        basename = self._normalize_for_basename_check(name)
        self._invalidate_on_basename_no_ext_changes.add(basename)

    def to_dict(self):
        libraries = {}
        for doc_uri, library_infos in self._doc_uri_to_library_infos.items():
            libraries[doc_uri] = [x.to_dict() for x in library_infos]

        resources = {}
        for doc_uri, resource_imports in self._doc_uri_to_resource_imports.items():
            resources[doc_uri] = [
                (doc.uri if doc else None) for (_node, doc) in resource_imports
            ]

        variables = {}
        for doc_uri, variable_imports in self._doc_uri_to_variable_imports.items():
            variables[doc_uri] = [
                (doc.uri if doc else None) for (_node, doc) in variable_imports
            ]

        ret = {
            "root_doc": self._root_doc.uri,
            "libraries": libraries,
            "resources": resources,
            "variables": variables,
        }
        return ret

    def print_repr(self):
        import json

        print(json.dumps(self.to_dict(), indent=4))

    def add_library_infos(
        self,
        doc_uri: str,
        library_infos: OrderedSet[LibraryDependencyInfo],
    ):
        self._doc_uri_to_library_infos[doc_uri] = library_infos
        self._invalidate_on_uri_changes.add(uris.normalize_uri(doc_uri))

    def add_resource_infos(
        self,
        doc_uri: str,
        resource_imports_as_docs: Sequence[
            Tuple[IResourceImportNode, Optional[IRobotDocument]]
        ],
    ):
        self._doc_uri_to_resource_imports[doc_uri] = resource_imports_as_docs

        self._invalidate_on_uri_changes.add(uris.normalize_uri(doc_uri))
        for _, resource_doc in resource_imports_as_docs:
            if resource_doc is not None:
                self._invalidate_on_uri_changes.add(
                    uris.normalize_uri(resource_doc.uri)
                )

    def add_variable_infos(
        self,
        doc_uri: str,
        new_variable_imports: Sequence[
            Tuple[IVariableImportNode, Optional[IRobotDocument]]
        ],
    ):
        self._doc_uri_to_variable_imports[doc_uri] = new_variable_imports

        self._invalidate_on_uri_changes.add(uris.normalize_uri(doc_uri))
        for _, variable_doc in new_variable_imports:
            if variable_doc is not None:
                self._invalidate_on_uri_changes.add(
                    uris.normalize_uri(variable_doc.uri)
                )

    def get_root_doc(self) -> IRobotDocument:
        return self._root_doc

    def iter_libraries(self, doc_uri: str) -> Iterator[LibraryDependencyInfo]:
        infos = self._doc_uri_to_library_infos.get(doc_uri)
        if infos:
            yield from infos

    def iter_all_libraries(self) -> Iterator[LibraryDependencyInfo]:
        for infos in self._doc_uri_to_library_infos.values():
            yield from infos

    def iter_resource_imports_with_docs(
        self, doc_uri: str
    ) -> Iterator[Tuple[IResourceImportNode, Optional[IRobotDocument]]]:
        infos = self._doc_uri_to_resource_imports.get(doc_uri)
        if infos:
            yield from infos

    def iter_all_resource_imports_with_docs(
        self,
    ) -> Iterator[Tuple[IResourceImportNode, Optional[IRobotDocument]]]:
        for infos in self._doc_uri_to_resource_imports.values():
            yield from infos

    def iter_variable_imports_as_docs(
        self, doc_uri: str
    ) -> Iterator[Tuple[IVariableImportNode, Optional[IRobotDocument]]]:
        variable_imports = self._doc_uri_to_variable_imports.get(doc_uri)
        if variable_imports:
            yield from variable_imports

    def iter_all_variable_imports_as_docs(
        self,
    ) -> Iterator[Tuple[IVariableImportNode, Optional[IRobotDocument]]]:
        for variable_imports in self._doc_uri_to_variable_imports.values():
            yield from variable_imports

    def do_invalidate_on_uri_change(self, uri: str) -> bool:
        if uris.normalize_uri(uri) == uris.normalize_uri(self.get_root_doc().uri):
            # Changes in the root don't invalidate the dependency info (rather
            # it's used in the cache key when checking so it won't be a match).
            return False

        if uris.normalize_uri(uri) in self._invalidate_on_uri_changes:
            return True

        basename = self._normalize_for_basename_check(uri)
        if basename in self._invalidate_on_basename_no_ext_changes:
            return True

        return False

    def _normalize_for_basename_check(self, name):
        if "}" in name:
            # Get everything after a variable to account for patterns such as ${/}.
            name = name.split("}")[-1]
        return os.path.basename(os.path.splitext(name)[0]).lower()

    @classmethod
    def _collect_library_info_from_completion_context(
        cls, curr_ctx: ICompletionContext, is_root_context: bool, memo: _Memo
    ) -> OrderedSet[LibraryDependencyInfo]:
        from robotframework_ls.impl import ast_utils
        from robot.api import Token

        # Collect libraries information
        libraries = curr_ctx.get_imported_libraries()

        new_library_infos: OrderedSet[LibraryDependencyInfo] = OrderedSet()
        if is_root_context:
            new_library_infos.add(
                LibraryDependencyInfo(BUILTIN_LIB, None, True, None, None)
            )

        for library in libraries:
            name_tok = library.get_token(Token.NAME)

            if name_tok and name_tok.value:
                alias = library.alias
                args = ast_utils.get_library_arguments_serialized(library)
                node = library

                resolved_name = curr_ctx.token_value_resolving_variables(name_tok)
                if curr_ctx.tracing:
                    log.debug(
                        "Collecting library with resolved name: %s (alias: %s)",
                        resolved_name,
                        alias,
                    )
                lib_info = LibraryDependencyInfo(
                    resolved_name,
                    alias,
                    False,
                    args,
                    node,
                )
                if not memo.complete_for_library(lib_info.name, lib_info.alias):
                    continue

                new_library_infos.add(lib_info)
        return new_library_infos

    @classmethod
    def _collect_resource_info_from_completion_context(
        cls, curr_ctx: ICompletionContext, is_root_context: bool, memo: _Memo
    ):
        # Collect related resource imports information.
        resource_imports_as_docs = curr_ctx.get_resource_imports_as_docs()
        new_resource_infos: List[
            Tuple[IResourceImportNode, Optional[IRobotDocument]]
        ] = []
        if resource_imports_as_docs:
            for resource_import_node, resource_doc in resource_imports_as_docs:
                if resource_doc is None:
                    if is_root_context:
                        # We need to keep the empty nodes for the initial context.
                        new_resource_infos.append((resource_import_node, resource_doc))
                elif memo.follow_import(resource_doc.uri):
                    new_resource_infos.append((resource_import_node, resource_doc))
        return new_resource_infos

    @classmethod
    def _collect_variable_info_from_completion_context(
        cls, curr_ctx: ICompletionContext, is_root_context: bool, memo: _Memo
    ) -> Sequence[Tuple[IVariableImportNode, Optional[IRobotDocument]]]:
        variable_imports_as_docs = curr_ctx.get_variable_imports_as_docs()
        new_variable_infos: List[
            Tuple[IVariableImportNode, Optional[IRobotDocument]]
        ] = []
        if variable_imports_as_docs:
            for variable_import_node, variable_doc in variable_imports_as_docs:
                if variable_doc is None:
                    if is_root_context:
                        # We need to keep the empty nodes for the initial context.
                        new_variable_infos.append((variable_import_node, variable_doc))
                elif memo.follow_import(variable_doc.uri):
                    new_variable_infos.append((variable_import_node, variable_doc))
        return new_variable_infos

    @classmethod
    def from_completion_context(
        cls, completion_context: ICompletionContext
    ) -> ICompletionContextDependencyGraph:
        from collections import deque
        from robot.api import Token

        caches: ICompletionContextWorkspaceCaches = (
            completion_context.workspace.completion_context_workspace_caches
        )

        memo = _Memo()
        with caches.invalidation_tracker() as invalidation_tracker:
            dependency_graph = CompletionContextDependencyGraph(completion_context.doc)

            initial_library_infos = cls._collect_library_info_from_completion_context(
                completion_context, is_root_context=True, memo=memo
            )

            # i.e.: Note that the cache key involves the import names, not the
            # import locations (so, in case there's a match we need to fix
            # the newly returned info).

            resource_imports = completion_context.get_resource_imports()
            variable_imports = completion_context.get_variable_imports()

            cache_key = (
                completion_context.doc.uri,
                tuple(
                    (info.name, info.alias, info.builtin, info.args)
                    for info in initial_library_infos
                ),
                tuple(
                    (
                        tuple(t.value for t in node.tokens if t.type == t.NAME)
                        for node in resource_imports
                    )
                ),
                tuple(
                    (
                        tuple(t.value for t in node.tokens if t.type == t.NAME)
                        for node in variable_imports
                    )
                ),
            )

            found = caches.get_cached_dependency_graph(cache_key)
            if found is not None:
                # We need to fix the nodes as we can match even when the node
                # lines/columns change.

                # Library infos for the root can be added again as is because we
                # just collected the whole info again (including the nodes).
                found.add_library_infos(
                    completion_context.doc.uri, initial_library_infos
                )

                # For resources, we don't want to add them completely because this
                # means that the resolution must be done again.
                names_to_resources: Dict[
                    Tuple[str, ...], List[IResourceImportNode]
                ] = {}

                for resource_import in completion_context.get_resource_imports():
                    key = tuple(x.value for x in resource_import.get_tokens(Token.NAME))
                    names_to_resources.setdefault(key, []).append(resource_import)

                new_resources: List[
                    Tuple[IResourceImportNode, Optional[IRobotDocument]]
                ] = []
                for (
                    resource_import,
                    resource_doc,
                ) in found.iter_resource_imports_with_docs(completion_context.doc.uri):
                    key = tuple(x.value for x in resource_import.get_tokens(Token.NAME))
                    lst = names_to_resources.get(key)
                    if lst:
                        resource_import = lst.pop()
                        new_resources.append((resource_import, resource_doc))

                found.add_resource_infos(completion_context.doc.uri, new_resources)

                # Variables don't need any change as we don't store the nodes.
                return found

            completion_context_stack: Deque[ICompletionContext] = deque()
            completion_context_stack.append(completion_context)

            is_root_context = True

            # Mark as being followed.
            memo.follow_import(completion_context.doc.uri)

            while completion_context_stack:
                curr_ctx = completion_context_stack.popleft()

                if is_root_context:
                    # use what's been already collected to compute the cache.
                    new_library_infos = initial_library_infos
                else:
                    new_library_infos = (
                        cls._collect_library_info_from_completion_context(
                            curr_ctx, is_root_context, memo
                        )
                    )
                new_resource_infos = cls._collect_resource_info_from_completion_context(
                    curr_ctx, is_root_context, memo
                )
                new_variable_imports = (
                    cls._collect_variable_info_from_completion_context(
                        curr_ctx, is_root_context, memo
                    )
                )

                if new_library_infos:
                    dependency_graph.add_library_infos(
                        curr_ctx.doc.uri, new_library_infos
                    )

                if new_resource_infos:
                    dependency_graph.add_resource_infos(
                        curr_ctx.doc.uri, new_resource_infos
                    )
                    for _resource_import_node, resource_doc in new_resource_infos:
                        if resource_doc is not None:
                            new_ctx = curr_ctx.create_copy(resource_doc)
                            completion_context_stack.append(new_ctx)

                if new_variable_imports:
                    dependency_graph.add_variable_infos(
                        curr_ctx.doc.uri, new_variable_imports
                    )

                for node in resource_imports:
                    for t in node.tokens:
                        if t.type == t.NAME:
                            dependency_graph.invalidate_on_basename_change(t.value)

                for n in variable_imports:
                    for t in n.tokens:
                        if t.type == t.NAME:
                            dependency_graph.invalidate_on_basename_change(t.value)

                for info in initial_library_infos:
                    dependency_graph.invalidate_on_basename_change(info.name)

                is_root_context = False

            cls.on_before_cache_dependency_graph(dependency_graph)
            caches.cache_dependency_graph(
                cache_key, dependency_graph, invalidation_tracker
            )
        return dependency_graph

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ICompletionContextDependencyGraph = check_implements(self)
