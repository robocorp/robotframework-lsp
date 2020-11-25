import logging
import os.path
import sys
import pytest
from robocorp_code.protocols import (
    LocalRobotMetadataInfoDict,
    WorkspaceInfoDict,
    ActionResult,
)
from typing import List
import time
from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
import py
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from robocorp_code_tests.fixtures import RccPatch

log = logging.getLogger(__name__)


@pytest.fixture
def initialization_options():
    return {"do-not-track": True}


def test_missing_message(
    language_server: IRobocorpLanguageServerClient, ws_root_path, initialization_options
):
    language_server.initialize(
        ws_root_path, initialization_options=initialization_options
    )

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
    language_server_process: IRobocorpLanguageServerClient,
    language_server_io,
    ws_root_path,
    initialization_options,
):
    """
    :note: Only check with the language_server_io (because that's in another process).
    """
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_ls_core.basic import is_process_alive
    from robocorp_ls_core.basic import kill_process_and_subprocesses
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    language_server = language_server_io
    dummy_process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(10000)"]
    )

    language_server.initialize(
        ws_root_path,
        process_id=dummy_process.pid,
        initialization_options=initialization_options,
    )

    assert is_process_alive(dummy_process.pid)
    assert is_process_alive(language_server_process.pid)

    kill_process_and_subprocesses(dummy_process.pid)

    wait_for_test_condition(lambda: not is_process_alive(dummy_process.pid))
    wait_for_test_condition(lambda: not is_process_alive(language_server_process.pid))
    language_server_io.require_exit_messages = False


@pytest.fixture
def language_server_initialized(
    language_server_tcp: IRobocorpLanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    ci_endpoint: str,
    rcc_config_location: str,
    initialization_options,
):
    from robocorp_code.commands import ROBOCORP_RUN_IN_RCC_INTERNAL

    language_server = language_server_tcp
    language_server.initialize(
        ws_root_path, initialization_options=initialization_options
    )
    language_server.settings(
        {
            "settings": {
                "robocorp": {
                    "rcc": {
                        "location": rcc_location,
                        "endpoint": ci_endpoint,
                        "config_location": rcc_config_location,
                    }
                }
            }
        }
    )
    result = language_server.execute_command(
        ROBOCORP_RUN_IN_RCC_INTERNAL,
        [
            {
                "args": "configure identity --do-not-track --config".split()
                + [rcc_config_location]
            }
        ],
    )
    assert result["result"]["success"]
    if "disabled" not in result["result"]["result"]:
        raise AssertionError(f"Unexpected result: {result}")

    return language_server


def test_list_rcc_robot_templates(
    language_server_initialized: IRobocorpLanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    tmpdir,
) -> None:
    from robocorp_code import commands

    assert os.path.exists(rcc_location)
    language_server = language_server_initialized

    result = language_server.execute_command(
        commands.ROBOCORP_LIST_ROBOT_TEMPLATES_INTERNAL, []
    )["result"]
    assert result["success"]
    assert result["result"] == [
        "Standard - Robot Framework Robot.",
        "Python - Python Robot.",
        "Extended - Robot Framework Robot with additional scaffolding.",
    ]

    target = str(tmpdir.join("dest"))
    language_server.change_workspace_folders(added_folders=[target], removed_folders=[])

    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ROBOT_INTERNAL,
        [
            {
                "directory": target,
                "name": "example",
                "template": "Standard - Robot Framework Robot.",
            }
        ],
    )["result"]
    assert result["success"]
    assert not result["message"]

    # Error
    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ROBOT_INTERNAL,
        [{"directory": target, "name": "example", "template": "standard"}],
    )["result"]
    assert not result["success"]
    assert "Error creating robot" in result["message"]
    assert "not empty" in result["message"]
    assert "b'" not in result["message"]

    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ROBOT_INTERNAL,
        [{"directory": ws_root_path, "name": "example2", "template": "standard"}],
    )["result"]
    assert result["success"]

    result = language_server.execute_command(
        commands.ROBOCORP_LOCAL_LIST_ROBOTS_INTERNAL, []
    )["result"]
    assert result["success"]
    folder_info_lst: List[LocalRobotMetadataInfoDict] = result["result"]
    assert len(folder_info_lst) == 2
    assert set([x["name"] for x in folder_info_lst]) == {"example", "example2"}


def get_workspace_from_name(
    workspace_list: List[WorkspaceInfoDict], workspace_name: str
) -> WorkspaceInfoDict:
    for ws in workspace_list:
        if ws["workspaceName"] == workspace_name:
            return ws
    raise AssertionError(f"Did not find workspace: {workspace_name}")


def _get_as_name_to_sort_key_and_package_id(lst: List[WorkspaceInfoDict]):
    name_to_sort_key = {}
    for workspace_info in lst:
        for package_info in workspace_info["packages"]:
            name_to_sort_key[package_info["name"]] = (
                package_info["sortKey"],
                package_info["id"],
            )
    return name_to_sort_key


def test_get_plugins_dir(language_server_initialized: IRobocorpLanguageServerClient,):
    client = language_server_initialized
    result = client.get_plugins_dir()

    assert result
    assert result.endswith("plugins")
    assert os.path.exists(result)


def test_cloud_list_workspaces_sorting(
    language_server_initialized: IRobocorpLanguageServerClient,
    rcc_patch: RccPatch,
    tmpdir: py.path.local,
):
    client = language_server_initialized
    root_dir = str(tmpdir.join("root").mkdir())

    rcc_patch.apply()

    result = client.cloud_list_workspaces()
    assert result["success"]
    ws_info = result["result"]
    assert ws_info

    ci_workspace_info = get_workspace_from_name(ws_info, "CI workspace")

    result = client.upload_to_new_robot(
        ci_workspace_info["workspaceId"],
        f"New package {time.time()}",
        "<dir not there>",
    )
    assert not result["success"]
    msg = result["message"]
    assert msg and "to exist" in msg

    result = client.upload_to_new_robot(
        ci_workspace_info["workspaceId"], "New package", root_dir
    )
    assert result["success"]

    result = client.cloud_list_workspaces()
    assert result["success"]

    res = result["result"]
    assert res
    assert _get_as_name_to_sort_key_and_package_id(res) == {
        "Package Name 1": ("00010package name 1", "452"),
        "Package Name 2": ("00010package name 2", "453"),
        "New package": ("00000new package", "2323"),
    }

    result = client.upload_to_existing_activity(
        ci_workspace_info["workspaceId"], "453", root_dir
    )
    assert result["success"]


def test_cloud_list_workspaces_basic(
    language_server_initialized: IRobocorpLanguageServerClient,
    rcc_patch: RccPatch,
    data_regression,
):

    client = language_server_initialized

    rcc_patch.apply()

    result1 = client.cloud_list_workspaces()
    assert result1["success"]

    data_regression.check(result1)

    rcc_patch.disallow_calls()
    result2 = client.cloud_list_workspaces()
    assert result2["success"]
    assert result1["result"] == result2["result"]

    result3 = client.cloud_list_workspaces(refresh=True)
    assert "message" in result3

    # Didn't work out because the mock forbids it (as expected).
    assert not result3["success"]
    msg = result3["message"]
    assert msg and "This should not be called at this time" in msg


def test_cloud_list_workspaces_errors_single_ws_not_available(
    language_server_initialized: IRobocorpLanguageServerClient,
    rcc_patch: RccPatch,
    data_regression,
):

    client = language_server_initialized

    def custom_handler(args, *sargs, **kwargs):
        if args[:4] == ["cloud", "workspace", "--workspace", "workspace_id_1"]:
            # List packages for workspace 1
            return ActionResult(
                success=False,
                message="""{"error":{"code":"WORKSPACE_TREE_NOT_FOUND","subCode":"","message":"workspace tree not found"}""",
                result=None,
            )

    rcc_patch.custom_handler = custom_handler
    rcc_patch.apply()

    result1 = client.cloud_list_workspaces()

    # i.e.: Should show only workspace 2 as workspace 1 errored.
    data_regression.check(result1)

    rcc_patch.custom_handler = None

    result2 = client.cloud_list_workspaces()
    assert result1["result"] == result2["result"]  # Use cached

    result3 = client.cloud_list_workspaces(refresh=True)
    data_regression.check(result3, basename="test_cloud_list_workspaces_basic")


def test_cloud_list_workspaces_errors_no_ws_available(
    language_server_initialized: IRobocorpLanguageServerClient, rcc_patch: RccPatch
):

    client = language_server_initialized

    def custom_handler(args, *sargs, **kwargs):
        if args[:3] == ["cloud", "workspace", "--workspace"]:
            # List packages for workspace 1
            return ActionResult(
                success=False,
                message="""{"error":{"code":"WORKSPACE_TREE_NOT_FOUND","subCode":"","message":"workspace tree not found"}""",
                result=None,
            )

    rcc_patch.custom_handler = custom_handler
    rcc_patch.apply()

    result1 = client.cloud_list_workspaces()

    assert not result1["success"]


def test_upload_to_cloud(
    language_server_initialized: IRobocorpLanguageServerClient,
    ci_credentials: str,
    ws_root_path: str,
    monkeypatch,
):
    from robocorp_code import commands
    from robocorp_code.protocols import PackageInfoDict
    from robocorp_code.rcc import Rcc

    client = language_server_initialized

    client.DEFAULT_TIMEOUT = 10  # The cloud may be slow.

    result = client.execute_command(commands.ROBOCORP_IS_LOGIN_NEEDED_INTERNAL, [])[
        "result"
    ]
    assert result["result"], "Expected login to be needed."

    result = client.execute_command(
        commands.ROBOCORP_CLOUD_LOGIN_INTERNAL, [{"credentials": "invalid"}]
    )["result"]
    assert not result["success"], "Expected login to be unsuccessful."

    result = client.execute_command(
        commands.ROBOCORP_CLOUD_LOGIN_INTERNAL, [{"credentials": ci_credentials}]
    )["result"]
    assert result["success"], "Expected login to be successful."

    result = client.cloud_list_workspaces()
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
    result = client.execute_command(
        commands.ROBOCORP_CREATE_ROBOT_INTERNAL,
        [{"directory": ws_root_path, "name": "example", "template": "standard"}],
    )["result"]
    assert result["success"]

    directory = os.path.join(ws_root_path, "example")
    result = client.upload_to_existing_activity(
        found_package["workspaceId"], found_package["id"], directory
    )
    assert result["success"]

    def mock_run_rcc(self, args, *sargs, **kwargs):
        if args[:3] == ["cloud", "new", "--workspace"]:
            return ActionResult(
                success=True,
                message=None,
                result="Created new robot named 'New package 1597082853.2224553' with identity 453.\n",
            )
        if args[:3] == ["cloud", "push", "--directory"]:
            return ActionResult(success=True, message=None, result="OK.\n")

        raise AssertionError(f"Unexpected args: {args}")

    # Note: it should work without the monkeypatch as is, but it'd create a dummy
    # package and we don't have an API to remove it.
    monkeypatch.setattr(Rcc, "_run_rcc", mock_run_rcc)

    result = client.upload_to_new_robot(
        found_package["workspaceId"], f"New package {time.time()}", directory
    )
    assert result["success"]


def test_lru_disk_commands(language_server_initialized: IRobocorpLanguageServerClient):
    from robocorp_code import commands

    client = language_server_initialized

    def save_to_lru(name: str, entry: str, lru_size: int):
        result = client.execute_command(
            commands.ROBOCORP_SAVE_IN_DISK_LRU,
            [{"name": name, "entry": entry, "lru_size": lru_size}],
        )["result"]

        assert result["success"]

    def get_from_lru(name: str) -> list:
        result = client.execute_command(
            commands.ROBOCORP_LOAD_FROM_DISK_LRU, [{"name": name}]
        )
        return result["result"]

    assert get_from_lru("my_lru") == []

    save_to_lru("my_lru", "entry1", lru_size=2)
    assert get_from_lru("my_lru") == ["entry1"]

    save_to_lru("my_lru", "entry2", lru_size=2)
    assert get_from_lru("my_lru") == ["entry2", "entry1"]

    save_to_lru("my_lru", "entry1", lru_size=2)
    assert get_from_lru("my_lru") == ["entry1", "entry2"]

    save_to_lru("my_lru", "entry3", lru_size=2)
    assert get_from_lru("my_lru") == ["entry3", "entry1"]


def _compute_robot_launch_from_robocorp_code_launch(
    client: IRobocorpLanguageServerClient, task: str, robot: str, **kwargs
):
    from robocorp_code import commands

    args = {"robot": robot, "task": task, "name": "Launch Name", "request": "launch"}
    args.update(kwargs)
    result = client.execute_command(
        commands.ROBOCORP_COMPUTE_ROBOT_LAUNCH_FROM_ROBOCORP_CODE_LAUNCH, [args]
    )["result"]
    return result


def test_compute_robot_launch_from_robocorp_code_launch(
    language_server_initialized: IRobocorpLanguageServerClient, cases: CasesFixture
):
    client = language_server_initialized

    robot = cases.get_path("custom_envs/simple-web-scraper/robot.yaml")
    result = _compute_robot_launch_from_robocorp_code_launch(
        client, "Web scraper", robot
    )
    assert result["success"]
    r = result["result"]

    assert os.path.samefile(
        r["target"], cases.get_path("custom_envs/simple-web-scraper/tasks")
    )
    assert os.path.samefile(r["cwd"], cases.get_path("custom_envs/simple-web-scraper"))
    del r["target"]
    del r["cwd"]

    assert r == {
        "type": "robotframework-lsp",
        "name": "Launch Name",
        "request": "launch",
        "args": ["-d", "output", "--logtitle", "Task log"],
        "terminal": "none",
    }


def test_compute_python_launch_from_robocorp_code_launch(
    language_server_initialized: IRobocorpLanguageServerClient, cases: CasesFixture
):
    client = language_server_initialized

    robot = cases.get_path("custom_envs/pysample/robot.yaml")
    result = _compute_robot_launch_from_robocorp_code_launch(
        client, "Default", robot, pythonExe="c:/temp/py.exe"
    )
    assert result["success"]
    r = result["result"]

    assert os.path.samefile(
        r["program"], cases.get_path("custom_envs/pysample/task.py")
    )
    assert os.path.samefile(r["cwd"], cases.get_path("custom_envs/pysample"))
    del r["program"]
    del r["cwd"]

    assert r == {
        "type": "python",
        "name": "Launch Name",
        "request": "launch",
        "pythonArgs": [],
        "args": [],
        "pythonPath": "c:/temp/py.exe",
        "console": "internalConsole",
    }
