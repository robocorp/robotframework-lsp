from robocorp_code.protocols import IRcc, IRccActivity
import py.path


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


def test_rcc_run_with_package_yaml(rcc: IRcc, rcc_conda_installed):
    python_code = """
import sys
sys.stdout.write('It worked')
"""

    conda_yaml_str_contents = """
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.7.5
"""

    result = rcc.run_python_code_package_yaml(python_code, conda_yaml_str_contents)
    assert result.success
    assert result.result
    # Note: even in silent mode we may have additional output!
    assert "It worked" in result.result


def test_numbered_dir(tmpdir):
    from robocorp_code.rcc import make_numbered_in_temp
    from pathlib import Path
    import time

    registered = []
    from functools import partial

    def register(func, *args, **kwargs):
        registered.append(partial(func, *args, **kwargs))

    n = make_numbered_in_temp(
        keep=2, lock_timeout=0.01, tmpdir=Path(tmpdir), register=register
    )

    # Sleep so that it'll be scheduled for removal at the next creation.
    time.sleep(0.02)
    assert n.name.endswith("-0")
    assert n.is_dir()

    n = make_numbered_in_temp(
        keep=2, lock_timeout=0.01, tmpdir=Path(tmpdir), register=register
    )
    assert n.name.endswith("-1")
    assert n.is_dir()

    n = make_numbered_in_temp(
        keep=2, lock_timeout=0.01, tmpdir=Path(tmpdir), register=register
    )
    assert n.name.endswith("-2")
    assert n.is_dir()

    # Removed dir 0.
    assert len(list(n.parent.iterdir())) == 3
    for r in registered:
        r()
    assert len(list(n.parent.iterdir())) == 2
