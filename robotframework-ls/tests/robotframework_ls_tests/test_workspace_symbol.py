def test_workspace_symbols(workspace, libspec_manager):
    from robotframework_ls.impl.workspace_symbols import workspace_symbols
    from robotframework_ls.impl.completion_context import BaseContext
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.config import Config

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = doc.source + "\n    Should Be Empty"

    config = Config()

    symbols = workspace_symbols("", BaseContext(workspace.ws, config, NULL))
    assert len(symbols) > 0
