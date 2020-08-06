from robocode_ls_core.protocols import IConfigProvider
import pytest
from robocode_vscode.protocols import IRcc, IRccActivity
import py.path


class _ConfigProvider(object):
    def __init__(self, config):
        self.config = config


@pytest.fixture
def config_provider(
    ws_root_path: str, rcc_location: str, ci_endpoint: str, rcc_config_location: str
):
    from robocode_ls_core.config import Config
    from robocode_ls_core import uris

    config = Config(uris.from_fs_path(ws_root_path))

    config.update(
        {
            "robocode": {
                "rcc": {
                    "location": rcc_location,
                    "endpoint": ci_endpoint,
                    "config_location": rcc_config_location,
                }
            }
        }
    )
    return _ConfigProvider(config)


@pytest.fixture
def rcc(config_provider: IConfigProvider) -> IRcc:
    from robocode_vscode.rcc import Rcc

    rcc = Rcc(config_provider)
    return rcc


def test_rcc_template_names(rcc: IRcc):
    result = rcc.get_template_names()
    assert result.success
    assert result.result
    assert "minimal" in result.result


def test_rcc_cloud(rcc: IRcc, ci_credentials: str, tmpdir: py.path.local):
    assert not rcc.credentials_valid()
    result = rcc.add_credentials(ci_credentials)
    assert result.success
    assert rcc.credentials_valid()

    result = rcc.cloud_list_workspaces()
    assert result.success

    workspaces = result.result
    if not workspaces:
        raise AssertionError("Expected to have CI Workspace available.")
    workspaces = [ws for ws in workspaces if ws.workspace_name == "CI workspace"]
    if not workspaces:
        raise AssertionError("Expected to have CI Workspace available.")

    ws = workspaces[0]
    result = rcc.cloud_list_workspace_activities(ws.workspace_id)
    assert result.success
    lst = result.result
    if lst is None:
        raise AssertionError("Found no workspace")

    acts = [act for act in lst if act.activity_name == "CI activity"]
    if not acts:
        result = rcc.cloud_create_activity(ws.workspace_id, "CI activity")
        assert result.success
        result = rcc.cloud_list_workspace_activities(ws.workspace_id)
        assert result.success
        lst = result.result
        if lst is None:
            raise AssertionError("Found no activity")
        acts = [act for act in lst if act.activity_name == "CI activity"]
    if not acts:
        raise AssertionError(
            "Expected to be able to create CI activity (or have it there already)."
        )
    act: IRccActivity = acts[0]

    wsdir = str(tmpdir.join("ws"))

    result = rcc.create_activity("minimal", wsdir)
    assert result.success
    result = rcc.cloud_set_activity_contents(wsdir, ws.workspace_id, act.activity_id)
    assert result.success
