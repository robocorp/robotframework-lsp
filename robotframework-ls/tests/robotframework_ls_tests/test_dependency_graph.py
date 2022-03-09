from robotframework_ls.impl.protocols import (
    IRobotWorkspace,
    ICompletionContextWorkspaceCaches,
    ICompletionContextDependencyGraph,
    ILibraryImportNode,
)
from typing import Optional
import pytest


def _nodes_info_to_compare(dependency_graph: ICompletionContextDependencyGraph):
    root_doc = dependency_graph.get_root_doc()

    libraries = []
    for info in dependency_graph.iter_libraries(root_doc.uri):
        library_node: Optional[ILibraryImportNode] = info.node
        if not library_node:
            continue
        libraries.append(
            {
                "name": library_node.name,
                "alias": library_node.alias,
                "lineno": library_node.lineno,
                "end_lineno": library_node.end_lineno,
                "col_offset": library_node.col_offset,
                "end_col_offset": library_node.end_col_offset,
            }
        )

    resources = []
    for resource_node, _doc in dependency_graph.iter_resource_imports_with_docs(
        root_doc.uri
    ):
        resources.append(
            {
                "name": resource_node.name,
                "lineno": resource_node.lineno,
                "end_lineno": resource_node.end_lineno,
                "col_offset": resource_node.col_offset,
                "end_col_offset": resource_node.end_col_offset,
            }
        )
    return {"libraries": libraries, "resources": resources}


def check_nodes(initial_nodes_info, dependency_graph, must_equal=True):
    if must_equal:
        assert initial_nodes_info == _nodes_info_to_compare(dependency_graph)
    else:
        new_info = _nodes_info_to_compare(dependency_graph)
        for key in ["libraries", "resources"]:
            try:
                assert initial_nodes_info[key] != new_info[key]
            except AssertionError:
                raise AssertionError(f"Error comparing: {key}")


@pytest.fixture
def _log_caches_ctx():
    from robocorp_ls_core.options import BaseOptions

    original = BaseOptions.DEBUG_CACHE_DEPS
    BaseOptions.DEBUG_CACHE_DEPS = True
    yield
    BaseOptions.DEBUG_CACHE_DEPS = original


def test_dependency_graph_caches_basic(workspace, _log_caches_ctx):
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case_deps")
    doc = workspace.get_doc("root.robot")

    context = CompletionContext(doc, workspace=workspace.ws)
    dependency_graph = context.collect_dependency_graph()
    initial_dict = dependency_graph.to_dict()
    initial_nodes_info = _nodes_info_to_compare(dependency_graph)

    # Step 1: change nothing -> contents should be gotten from the cache.
    ws: IRobotWorkspace = workspace.ws
    caches: ICompletionContextWorkspaceCaches = ws.completion_context_workspace_caches

    context = CompletionContext(doc, workspace=workspace.ws)
    dependency_graph = context.collect_dependency_graph()
    assert initial_dict == dependency_graph.to_dict()
    check_nodes(initial_nodes_info, dependency_graph)

    assert caches.cache_hits == 1

    # Same thing but add an additional new line in each line.
    new_doc_contents = "\n\n".join(
        doc.source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    )
    doc = workspace.put_doc("root.robot", new_doc_contents)

    context = CompletionContext(doc, workspace=workspace.ws)
    dependency_graph = context.collect_dependency_graph()

    assert caches.cache_hits == 2
    assert initial_dict == dependency_graph.to_dict()
    # The nodes must have changed!
    check_nodes(initial_nodes_info, dependency_graph, False)

    # Ok, up until now all is ok, caches found all the time. Let's check
    # for the invalidation strategies.

    # Change dependent document (cache will be invalidated).
    workspace.put_doc("my_resource.robot", "")

    context = CompletionContext(doc, workspace=workspace.ws)
    dependency_graph = context.collect_dependency_graph()

    assert caches.cache_hits == 2  # No hit!


def test_dependency_graph_caches_changes_during_compute(workspace):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.completion_context_dependency_graph import (
        CompletionContextDependencyGraph,
    )

    workspace.set_root("case_deps")
    doc = workspace.get_doc("root.robot")

    context = CompletionContext(doc, workspace=workspace.ws)

    # Now, setup things so that when the compute happens we change a dependency
    # (this means that the entry shouldn't even be cached as it was invalidated
    # while in-flight).
    def do_invalidate(dependency_graph):
        # Change dependent document (cache will be invalidated).
        workspace.put_doc("my_resource.robot", "")

    CompletionContextDependencyGraph.on_before_cache_dependency_graph.register(
        do_invalidate
    )
    try:
        dependency_graph = context.collect_dependency_graph()
    finally:
        CompletionContextDependencyGraph.on_before_cache_dependency_graph.unregister(
            do_invalidate
        )

    # Now, because there was an in-flight change the cache shouldn't be valid.
    ws: IRobotWorkspace = workspace.ws
    caches: ICompletionContextWorkspaceCaches = ws.completion_context_workspace_caches

    context = CompletionContext(doc, workspace=workspace.ws)
    assert caches.cache_hits == 0
    dependency_graph = context.collect_dependency_graph()
    assert caches.cache_hits == 0
