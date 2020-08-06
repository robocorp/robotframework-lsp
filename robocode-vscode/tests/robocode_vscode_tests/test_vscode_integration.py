import logging
from robocode_ls_core.protocols import ILanguageServerClient
import os.path
import sys
import pytest
from robocode_vscode.protocols import ActivityInfoDict, UploadActivityParamsDict
from typing import List

log = logging.getLogger(__name__)


def test_missing_message(language_server: ILanguageServerClient, ws_root_path):
    language_server.initialize(ws_root_path)

    # Just ignore this one (it's not a request because it has no id).
    language_server.write(
        {
            "jsonrpc": "2.0",
            "method": "invalidMessageSent",
            "params": {"textDocument": {"uri": "untitled:Untitled-1", "version": 2}},
        }
    )

    # Make sure that we have a response if it's a request (i.e.: it has an id).
    msg = language_server.request(
        {
            "jsonrpc": "2.0",
            "id": "22",
            "method": "invalidMessageSent",
            "params": {"textDocument": {"uri": "untitled:Untitled-1", "version": 2}},
        }
    )

    assert msg["error"]["code"] == -32601


def test_exit_with_parent_process_died(
    language_server_process: ILanguageServerClient, language_server_io, ws_root_path
):
    """
    :note: Only check with the language_server_io (because that's in another process).
    """
    from robocode_ls_core.subprocess_wrapper import subprocess
    from robocode_ls_core.basic import is_process_alive
    from robocode_ls_core.basic import kill_process_and_subprocesses
    from robocode_ls_core.unittest_tools.fixtures import wait_for_test_condition

    language_server = language_server_io
    dummy_process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(10000)"]
    )

    language_server.initialize(ws_root_path, process_id=dummy_process.pid)

    assert is_process_alive(dummy_process.pid)
    assert is_process_alive(language_server_process.pid)

    kill_process_and_subprocesses(dummy_process.pid)

    wait_for_test_condition(lambda: not is_process_alive(dummy_process.pid))
    wait_for_test_condition(lambda: not is_process_alive(language_server_process.pid))
    language_server_io.require_exit_messages = False


@pytest.fixture
def language_server_initialized(
    language_server_tcp: ILanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    ci_endpoint: str,
    rcc_config_location: str,
):
    language_server = language_server_tcp
    language_server.initialize(ws_root_path)
    language_server.settings(
        {
            "settings": {
                "robocode": {
                    "rcc": {
                        "location": rcc_location,
                        "endpoint": ci_endpoint,
                        "config_location": rcc_config_location,
                    }
                }
            }
        }
    )
    return language_server


def test_list_rcc_activity_templates(
    language_server_initialized: ILanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    tmpdir,
) -> None:
    from robocode_vscode import commands

    assert os.path.exists(rcc_location)
    language_server = language_server_initialized

    result = language_server.execute_command(
        commands.ROBOCODE_LIST_ACTIVITY_TEMPLATES_INTERNAL, []
    )["result"]
    assert result["success"]
    assert result["result"] == ["basic", "minimal"]

    target = str(tmpdir.join("dest"))
    language_server.change_workspace_folders(added_folders=[target], removed_folders=[])

    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    assert result["success"]
    assert not result["message"]

    # Error
    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    assert not result["success"]
    assert "Error creating activity" in result["message"]
    assert "not empty" in result["message"]
    assert "b'" not in result["message"]

    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": ws_root_path, "name": "example2", "template": "minimal"}],
    )["result"]
    assert result["success"]

    result = language_server.execute_command(
        commands.ROBOCODE_LOCAL_LIST_ACTIVITIES_INTERNAL, []
    )["result"]
    assert result["success"]
    folder_info_lst: List[ActivityInfoDict] = result["result"]
    assert len(folder_info_lst) == 2
    assert set([x["name"] for x in folder_info_lst]) == {"example", "example2"}


def test_upload_to_cloud(
    language_server_initialized: ILanguageServerClient,
    ci_credentials: str,
    ws_root_path: str,
):
    from robocode_vscode import commands
    from robocode_vscode.protocols import WorkspaceInfoDict
    from robocode_vscode.protocols import PackageInfoDict

    language_server = language_server_initialized

    language_server.DEFAULT_TIMEOUT = 10  # The cloud may be slow.

    result = language_server.execute_command(
        commands.ROBOCODE_IS_LOGIN_NEEDED_INTERNAL, []
    )["result"]
    assert result, "Expected login to be needed."

    result = language_server.execute_command(
        commands.ROBOCODE_CLOUD_LOGIN_INTERNAL, [{"credentials": "invalid"}]
    )["result"]
    assert not result["success"], "Expected login to be unsuccessful."

    result = language_server.execute_command(
        commands.ROBOCODE_CLOUD_LOGIN_INTERNAL, [{"credentials": ci_credentials}]
    )["result"]
    assert result["success"], "Expected login to be successful."

    result = language_server.execute_command(
        commands.ROBOCODE_CLOUD_LIST_WORKSPACES_INTERNAL,
        [{"refresh": False, "packages": True}],
    )["result"]
    assert result["success"]
    result_workspaces: List[WorkspaceInfoDict] = result["result"]
    assert result_workspaces, "Expected to have the available workspaces and packages."
    found = [x for x in result_workspaces if x["workspaceName"] == "CI workspace"]
    assert (
        len(found) == 1
    ), f'Expected to find "CI workspace". Found: {result_workspaces}'

    found_packages = [x for x in found[0]["packages"] if x["name"] == "CI activity"]
    assert (
        len(found_packages) == 1
    ), f'Expected to find "CI activity". Found: {result_workspaces}'

    found_package: PackageInfoDict = found_packages[0]
    result = language_server.execute_command(
        commands.ROBOCODE_CREATE_ACTIVITY_INTERNAL,
        [{"directory": ws_root_path, "name": "example", "template": "minimal"}],
    )["result"]
    assert result["success"]

    directory = os.path.join(ws_root_path, "example")
    params: UploadActivityParamsDict = {
        "workspaceId": found_package["workspaceId"],
        "packageId": found_package["id"],
        "directory": directory,
    }
    result = language_server.execute_command(
        commands.ROBOCODE_UPLOAD_TO_EXISTING_ACTIVITY_INTERNAL, [params]
    )["result"]
    assert result["success"]
