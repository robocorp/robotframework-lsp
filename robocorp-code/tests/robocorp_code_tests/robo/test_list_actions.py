import os

from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
from robocorp_ls_core import uris


def test_list_actions(
    language_server_initialized: IRobocorpLanguageServerClient,
    ws_root_path,
    cases,
    data_regression,
):
    from robocorp_code import commands

    cases.copy_to("action_package", ws_root_path)

    language_server = language_server_initialized
    result = language_server.execute_command(
        commands.ROBOCORP_LIST_ACTIONS_INTERNAL,
        [{"action_package": uris.from_fs_path(ws_root_path)}],
    )["result"]
    result["result"][0]["uri"] = os.path.basename(result["result"][0]["uri"])
    data_regression.check(result)
