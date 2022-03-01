from typing import Iterator, Tuple, Optional, Deque, Dict, Sequence, List

from robocorp_ls_core.ordered_set import OrderedSet
from robotframework_ls.impl.protocols import (
    ICompletionContextDependencyGraph,
    LibraryDependencyInfo,
    ICompletionContext,
    IResourceImportNode,
    IRobotDocument,
)
from robotframework_ls.impl.robot_constants import BUILTIN_LIB


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

    def __init__(self, root_doc: IRobotDocument):
        self._root_doc: IRobotDocument = root_doc
        self._doc_uri_to_library_infos: Dict[
            str, OrderedSet[LibraryDependencyInfo]
        ] = {}
        self._doc_uri_to_resource_imports: Dict[
            str, Sequence[Tuple[IResourceImportNode, Optional[IRobotDocument]]]
        ] = {}
        self._doc_uri_to_variable_imports: Dict[str, List[IRobotDocument]] = {}

    def add_library_infos(
        self,
        doc_uri: str,
        library_infos: OrderedSet[LibraryDependencyInfo],
    ):
        self._doc_uri_to_library_infos[doc_uri] = library_infos

    def add_resource_infos(
        self,
        doc_uri: str,
        resource_imports_as_docs: Sequence[
            Tuple[IResourceImportNode, Optional[IRobotDocument]]
        ],
    ):
        self._doc_uri_to_resource_imports[doc_uri] = resource_imports_as_docs

    def add_variable_infos(
        self, doc_uri: str, new_variable_imports: List[IRobotDocument]
    ):
        self._doc_uri_to_variable_imports[doc_uri] = new_variable_imports

    def get_root_doc(self) -> IRobotDocument:
        return self._root_doc

    def iter_libraries(self, doc_uri: str) -> Iterator[LibraryDependencyInfo]:
        info = self._doc_uri_to_library_infos.get(doc_uri)
        if info:
            yield from info

    def iter_resource_imports_as_docs(
        self,
    ) -> Iterator[Tuple[IResourceImportNode, Optional[IRobotDocument]]]:
        for infos in self._doc_uri_to_resource_imports.values():
            yield from infos

    def iter_variable_imports_as_docs(
        self,
    ) -> Iterator[IRobotDocument]:
        for variable_imports in self._doc_uri_to_variable_imports.values():
            yield from variable_imports

    @classmethod
    def from_completion_context(cls, completion_context: ICompletionContext):
        from robotframework_ls.impl import ast_utils
        from collections import deque

        dependency_graph = CompletionContextDependencyGraph(completion_context.doc)

        completion_context_stack: Deque[ICompletionContext] = deque()
        completion_context_stack.append(completion_context)

        memo = _Memo()
        initial_context = True

        # Mark as being followed.
        memo.follow_import(completion_context.doc.uri)

        while completion_context_stack:
            curr_ctx = completion_context_stack.popleft()

            # Collect libraries information
            libraries = curr_ctx.get_imported_libraries()

            # Note: using a dict(_LibInfo:bool) where only the keys are meaningful
            # because we want to keep the order and sets aren't ordered.
            library_infos: OrderedSet[LibraryDependencyInfo] = OrderedSet()
            if initial_context:
                library_infos.add(
                    LibraryDependencyInfo(BUILTIN_LIB, None, True, None, None)
                )

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
                    lib_info = LibraryDependencyInfo(
                        curr_ctx.token_value_resolving_variables(name),
                        alias,
                        False,
                        args,
                        node,
                    )
                    if not memo.complete_for_library(lib_info.name, lib_info.alias):
                        continue

                    library_infos.add(lib_info)

            if library_infos:
                dependency_graph.add_library_infos(curr_ctx.doc.uri, library_infos)

            # Collect related resource imports information.
            resource_imports_as_docs = curr_ctx.get_resource_imports_as_docs()
            if resource_imports_as_docs:
                new_resource_infos: List[
                    Tuple[IResourceImportNode, Optional[IRobotDocument]]
                ] = []

                for resource_import_node, resource_doc in resource_imports_as_docs:
                    if resource_doc is None:
                        if initial_context:
                            # We need to keep the empty nodes for the initial context.
                            new_resource_infos.append(
                                (resource_import_node, resource_doc)
                            )
                    elif memo.follow_import(resource_doc.uri):
                        new_resource_infos.append((resource_import_node, resource_doc))

                        new_ctx = curr_ctx.create_copy(resource_doc)
                        completion_context_stack.append(new_ctx)

                if new_resource_infos:
                    dependency_graph.add_resource_infos(
                        curr_ctx.doc.uri, new_resource_infos
                    )

            new_variable_imports: List[IRobotDocument] = []
            for variable_import in completion_context.get_variable_imports_as_docs():
                if memo.follow_import_variables(variable_import.uri):
                    new_variable_imports.append(variable_import)

            if new_variable_imports:
                dependency_graph.add_variable_infos(
                    curr_ctx.doc.uri, new_variable_imports
                )

            initial_context = False

        return dependency_graph

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: ICompletionContextDependencyGraph = check_implements(self)
