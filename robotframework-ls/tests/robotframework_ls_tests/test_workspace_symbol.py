def check_symbol(symbols, name):
    for symbol in symbols:
        if symbol["name"] == name:
            return

    raise AssertionError(f"Did not find: {name}")


def test_workspace_symbols(workspace, libspec_manager):
    from robotframework_ls.impl.workspace_symbols import workspace_symbols
    from robotframework_ls.impl.completion_context import BaseContext
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.config import Config

    workspace.set_root("case4", libspec_manager=libspec_manager)

    config = Config()

    symbols = workspace_symbols("", BaseContext(workspace.ws, config, NULL))
    assert len(symbols) > 0

    check_symbol(symbols, "List Files In Directory")
    check_symbol(symbols, "Yet Another Equal Redefined")

    symbols2 = workspace_symbols("", BaseContext(workspace.ws, config, NULL))
    assert symbols == symbols2

    symbols3 = workspace_symbols(
        "Yet Another Equal", BaseContext(workspace.ws, config, NULL)
    )

    # i.e.: Expect the client to filter it afterwards.
    assert symbols == symbols3
