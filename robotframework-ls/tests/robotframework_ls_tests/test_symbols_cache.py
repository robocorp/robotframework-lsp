def test_symbols_cache_basic(workspace, libspec_manager):
    from robotframework_ls.impl.completion_context import BaseContext
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.config import Config
    from robotframework_ls.impl.workspace_symbols import iter_symbols_caches

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    Log    ${SOME_GLOBAL_VAR}
"""

    doc2 = workspace.put_doc("case2a.robot")
    doc2.source = """
*** Keywords ***
Some Keyword
    Set Global Variable    ${some globalvar}
"""

    config = Config()
    context = BaseContext(workspace.ws, config, NULL)

    found = set()
    for symbols_cache in iter_symbols_caches("", context):
        uri = symbols_cache.get_uri()
        if uri is not None:
            if uri.endswith("case2a.robot"):
                found.add("case2a.robot")
                assert symbols_cache.has_global_variable_definition("someglobalvar")
                assert not symbols_cache.has_variable_reference("someglobalvar")

            elif uri.endswith("case2.robot"):
                found.add("case2.robot")
                assert not symbols_cache.has_global_variable_definition("someglobalvar")
                assert symbols_cache.has_variable_reference("someglobalvar")


def test_symbols_cache_inverse_index(workspace, libspec_manager):
    from robocorp_ls_core.config import Config
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case2", libspec_manager=libspec_manager, index_workspace=True)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    Log    ${SOME_GLOBAL_VAR}
"""

    doc2 = workspace.put_doc("case2a.robot")
    doc2.source = """
*** Keywords ***
Some Keyword
    Set Global Variable    ${some globalvar}
"""

    config = Config()
    context = CompletionContext(doc, workspace=workspace.ws, config=config)

    workspace_indexer = workspace.ws.workspace_indexer
    assert workspace_indexer

    symbols_cache_reverse_index = workspace_indexer.symbols_cache_reverse_index
    assert symbols_cache_reverse_index
    assert not symbols_cache_reverse_index.has_global_variable("someglobalvar")

    reverse_index = context.obtain_symbols_cache_reverse_index()
    assert reverse_index is symbols_cache_reverse_index
    assert reverse_index.has_global_variable("someglobalvar")
    assert reverse_index._reindex_count == 1

    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 1

    symbols_cache_reverse_index.notify_uri_changed(doc.uri)
    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 1

    symbols_cache_reverse_index.notify_uri_changed("foo")
    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 2

    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 2

    symbols_cache_reverse_index.notify_uri_changed("foo")
    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 3

    symbols_cache_reverse_index.request_full_reindex()
    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 4

    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 4

    reverse_index.synchronize(context)
    assert reverse_index._reindex_count == 4
