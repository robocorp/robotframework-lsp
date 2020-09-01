import logging
import os.path
import sys
import pytest
from robocorp_code.protocols import ActivityInfoDict, WorkspaceInfoDict, ActionResult
from typing import List
import time
from robocorp_code_tests.protocols import IRobocorpLanguageServerClient
import py

log = logging.getLogger(__name__)


def test_missing_message(language_server: IRobocorpLanguageServerClient, ws_root_path):
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
    language_server_process: IRobocorpLanguageServerClient,
    language_server_io,
    ws_root_path,
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

    language_server.initialize(ws_root_path, process_id=dummy_process.pid)

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
):
    language_server = language_server_tcp
    language_server.initialize(ws_root_path)
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
    return language_server


def test_list_rcc_activity_templates(
    language_server_initialized: IRobocorpLanguageServerClient,
    ws_root_path: str,
    rcc_location: str,
    tmpdir,
) -> None:
    from robocorp_code import commands

    assert os.path.exists(rcc_location)
    language_server = language_server_initialized

    result = language_server.execute_command(
        commands.ROBOCORP_LIST_ACTIVITY_TEMPLATES_INTERNAL, []
    )["result"]
    assert result["success"]
    assert result["result"] == ["basic", "minimal"]

    target = str(tmpdir.join("dest"))
    language_server.change_workspace_folders(added_folders=[target], removed_folders=[])

    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    assert result["success"]
    assert not result["message"]

    # Error
    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ACTIVITY_INTERNAL,
        [{"directory": target, "name": "example", "template": "minimal"}],
    )["result"]
    assert not result["success"]
    assert "Error creating activity" in result["message"]
    assert "not empty" in result["message"]
    assert "b'" not in result["message"]

    result = language_server.execute_command(
        commands.ROBOCORP_CREATE_ACTIVITY_INTERNAL,
        [{"directory": ws_root_path, "name": "example2", "template": "minimal"}],
    )["result"]
    assert result["success"]

    result = language_server.execute_command(
        commands.ROBOCORP_LOCAL_LIST_ACTIVITIES_INTERNAL, []
    )["result"]
    assert result["success"]
    folder_info_lst: List[ActivityInfoDict] = result["result"]
    assert len(folder_info_lst) == 2
    assert set([x["name"] for x in folder_info_lst]) == {"example", "example2"}


_WS_INFO = (
    {
        "id": "workspace_id_1",
        "name": "CI workspace",
        "orgId": "affd282c8f9fe",
        "orgName": "My Org Name",
        "orgShortName": "654321",
        "shortName": "123456",  # Can be some generated number or something provided by the user.
        "state": "active",
        "url": "http://url1",
    },
    {
        "id": "workspace_id_2",
        "name": "My Other workspace",
        "orgId": "affd282c8f9fe",
        "orgName": "My Org Name",
        "orgShortName": "1234567",
        "shortName": "7654321",
        "state": "active",
        "url": "http://url2",
    },
)

_PACKAGE_INFO_WS_2: dict = {}

_PACKAGE_INFO_WS_1: dict = {
    "activities": [
        {"id": "452", "name": "Package Name 1"},
        {"id": "453", "name": "Package Name 2"},
    ]
}


def get_workspace_from_name(
    workspace_list: List[WorkspaceInfoDict], workspace_name: str
) -> WorkspaceInfoDict:
    for ws in workspace_list:
        if ws["workspaceName"] == workspace_name:
            return ws
    raise AssertionError(f"Did not find workspace: {workspace_name}")


class RccPatch(object):
    def __init__(self, monkeypatch):
        from robocorp_code.rcc import Rcc

        self.monkeypatch = monkeypatch
        self._current_mock = self.mock_run_rcc_default
        self._original = Rcc._run_rcc
        self._package_info_ws_1 = _PACKAGE_INFO_WS_1

    def mock_run_rcc(self, args, *starargs, **kwargs) -> ActionResult:
        return self._current_mock(args, *starargs, **kwargs)

    def mock_run_rcc_default(self, args, *sargs, **kwargs) -> ActionResult:
        import json
        import copy

        if args[:4] == ["cloud", "workspace", "--workspace", "workspace_id_1"]:
            # List packages for workspace 1
            return ActionResult(
                success=True, message=None, result=json.dumps(self._package_info_ws_1)
            )

        if args[:4] == ["cloud", "workspace", "--workspace", "workspace_id_2"]:
            # List packages for workspace 2
            return ActionResult(
                success=True, message=None, result=json.dumps(_PACKAGE_INFO_WS_2)
            )

        if args[:3] == ["cloud", "workspace", "--config"]:
            # List workspaces
            workspace_info = _WS_INFO
            return ActionResult(
                success=True, message=None, result=json.dumps(workspace_info)
            )

        if args[:3] == ["cloud", "push", "--directory"]:
            if args[4:8] == ["--workspace", "workspace_id_1", "--package", "2323"]:
                return ActionResult(success=True)
            if args[4:8] == ["--workspace", "workspace_id_1", "--package", "453"]:
                return ActionResult(success=True)

        if args[:5] == ["cloud", "new", "--workspace", "workspace_id_1", "--package"]:
            # Submit a new package to ws 1
            cp = copy.deepcopy(self._package_info_ws_1)
            cp["activities"].append({"id": "2323", "name": args[5]})
            self._package_info_ws_1 = cp

            return ActionResult(
                success=True,
                message=None,
                result="Created new activity package named {args[5]} with identity 2323.",
            )

        raise AssertionError(f"Unexpected args: {args}")

    def mock_run_rcc_should_not_be_called(self, args, *sargs, **kwargs):
        raise AssertionError(
            "This should not be called at this time (data should be cached)."
        )

    def apply(self) -> None:
        from robocorp_code.rcc import Rcc

        self.monkeypatch.setattr(Rcc, "_run_rcc", self.mock_run_rcc)

    def disallow_calls(self) -> None:
        self._current_mock = self.mock_run_rcc_should_not_be_called


@pytest.fixture
def rcc_patch(monkeypatch):
    return RccPatch(monkeypatch)


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

    result = client.upload_to_new_activity(
        ci_workspace_info["workspaceId"],
        f"New package {time.time()}",
        "<dir not there>",
    )
    assert not result["success"]
    msg = result["message"]
    assert msg and "to exist" in msg

    result = client.upload_to_new_activity(
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
    language_server_initialized: IRobocorpLanguageServerClient, rcc_patch: RccPatch
):

    client = language_server_initialized

    rcc_patch.apply()

    result1 = client.cloud_list_workspaces()
    assert result1["success"]

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
        commands.ROBOCORP_CREATE_ACTIVITY_INTERNAL,
        [{"directory": ws_root_path, "name": "example", "template": "minimal"}],
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
                result="Created new activity package named 'New package 1597082853.2224553' with identity 453.\n",
            )
        if args[:3] == ["cloud", "push", "--directory"]:
            return ActionResult(success=True, message=None, result="OK.\n")

        raise AssertionError(f"Unexpected args: {args}")

    # Note: it should work without the monkeypatch as is, but it'd create a dummy
    # package and we don't have an API to remove it.
    monkeypatch.setattr(Rcc, "_run_rcc", mock_run_rcc)

    result = client.upload_to_new_activity(
        found_package["workspaceId"], f"New package {time.time()}", directory
    )
    assert result["success"]
