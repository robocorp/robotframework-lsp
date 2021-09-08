import py.path

from robocorp_code.protocols import IRcc, IRccRobotMetadata
import pytest
from pathlib import Path
import os
from robocorp_code.holetree_manager import UnableToGetSpaceName
import time
from dataclasses import dataclass
from typing import List

TIMEOUT_FOR_UPDATES_IN_SECONDS = 1
TIMEOUT_TO_REUSE_SPACE = 3
MAX_NUMBER_OF_SPACES = 2


def test_rcc_template_names(rcc: IRcc):
    result = rcc.get_template_names()
    assert result.success
    assert result.result
    assert "Standard - Robot Framework Robot." in result.result


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
    result = rcc.cloud_list_workspace_robots(ws.workspace_id)
    assert result.success
    lst = result.result
    if lst is None:
        raise AssertionError("Found no workspace")

    acts = [act for act in lst if act.robot_name == "CI activity"]
    if not acts:
        result = rcc.cloud_create_robot(ws.workspace_id, "CI activity")
        assert result.success
        result = rcc.cloud_list_workspace_robots(ws.workspace_id)
        assert result.success
        lst = result.result
        if lst is None:
            raise AssertionError("Found no activity")
        acts = [act for act in lst if act.robot_name == "CI activity"]
    if not acts:
        raise AssertionError(
            "Expected to be able to create CI activity (or have it there already)."
        )
    act: IRccRobotMetadata = acts[0]

    wsdir = str(tmpdir.join("ws"))

    result = rcc.create_robot("standard", wsdir)
    assert result.success
    result = rcc.cloud_set_robot_contents(wsdir, ws.workspace_id, act.robot_id)
    assert result.success


def test_numbered_dir(tmpdir):
    from robocorp_code.rcc import make_numbered_in_temp

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


@pytest.fixture
def holotree_manager(robocorp_home, rcc):
    from robocorp_code.holetree_manager import HolotreeManager

    vscode_path = Path(robocorp_home) / ".robocorp_code"
    holotree_manager = HolotreeManager(
        rcc,
        vscode_path,
        max_number_of_spaces=MAX_NUMBER_OF_SPACES,
        timeout_for_updates_in_seconds=TIMEOUT_FOR_UPDATES_IN_SECONDS,
        timeout_to_reuse_space=TIMEOUT_TO_REUSE_SPACE,
    )
    assert vscode_path.exists()
    return holotree_manager


def test_convert_robot_env_to_shell(tmpdir):
    import sys
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_code import _script_helpers

    robocorp_home = tmpdir.join("robohome")
    robo_env = {
        "PYTHON_EXE": sys.executable,
        "ROBOCORP_HOME": str(robocorp_home),
        "SOME_KEY": "SOME_VALUE",
    }
    code = _script_helpers.convert_robot_env_to_shell(robo_env)
    if sys.platform == "win32":
        shell_script = str(tmpdir.join("my.bat"))
    else:
        shell_script = str(tmpdir.join("my.sh"))

    _script_helpers.write_as_script(code, Path(shell_script))

    cmdline = [shell_script, "-c", 'import os;print(os.environ["SOME_KEY"])']

    try:
        output = subprocess.check_output(cmdline, shell=sys.platform == "win32")
        assert b"SOME_VALUE" in output
    except:
        sys.stderr.write(
            "Error when running: %s\n" % (" ".join(str(x) for x in cmdline),)
        )
        raise


@dataclass
class _RobotInfo:
    robot_yaml: Path
    conda_yaml: Path

    def __init__(self, datadir, robot_name):
        self.robot_yaml = datadir / robot_name / "robot.yaml"
        self.conda_yaml = datadir / robot_name / "conda.yaml"
        assert self.robot_yaml.exists()

    @property
    def conda_yaml_contents(self):
        return self.conda_yaml.read_text("utf-8")


def test_get_robot_yaml_environ(rcc: IRcc, datadir, holotree_manager):
    from robocorp_code.protocols import IRobotYamlEnvInfo
    from robocorp_ls_core.protocols import ActionResult
    from robocorp_code.protocols import IRCCSpaceInfo

    robot1 = _RobotInfo(datadir, "robot1")
    robot2 = _RobotInfo(datadir, "robot2")
    robot3 = _RobotInfo(datadir, "robot3")
    robot3_new_comment = _RobotInfo(datadir, "robot3_new_comment")

    space = holotree_manager.compute_valid_space_info(
        robot1.conda_yaml, robot1.conda_yaml_contents
    )
    assert space.space_name == "vscode-01"

    space = holotree_manager.compute_valid_space_info(
        robot2.conda_yaml, robot2.conda_yaml_contents
    )
    assert space.space_name == "vscode-02"

    space = holotree_manager.compute_valid_space_info(
        robot1.conda_yaml, robot1.conda_yaml_contents
    )
    assert space.space_name == "vscode-01"

    space_path_vscode01_conda: Path = holotree_manager._directory / "vscode-01" / "conda.yaml"
    space_path_vscode02_conda: Path = holotree_manager._directory / "vscode-02" / "conda.yaml"
    assert space_path_vscode01_conda.read_text("utf-8") == robot1.conda_yaml_contents
    assert space_path_vscode02_conda.read_text("utf-8") == robot2.conda_yaml_contents

    assert (holotree_manager._directory / "vscode-01" / "state").read_text(
        "utf-8"
    ) == "created"
    assert (holotree_manager._directory / "vscode-02" / "state").read_text(
        "utf-8"
    ) == "created"

    os.remove(space_path_vscode01_conda)

    # i.e.: vscode-01 is damaged and vscode-02 cannot be used because conda differs
    # and the needed timeout to reuse hasn't elapsed.
    with pytest.raises(UnableToGetSpaceName):
        holotree_manager.compute_valid_space_info(
            robot1.conda_yaml, robot1.conda_yaml_contents, require_timeout=True
        )

    # assert space_path_vscode01_conda.read_text("utf-8") == robot1.conda_yaml_contents
    assert space_path_vscode02_conda.read_text("utf-8") == robot2.conda_yaml_contents

    assert (holotree_manager._directory / "vscode-01" / "damaged").exists()

    # After the given timeout we can reuse the damaged one.
    time.sleep(TIMEOUT_TO_REUSE_SPACE + 0.01)
    space = holotree_manager.compute_valid_space_info(
        robot1.conda_yaml, robot1.conda_yaml_contents
    )
    assert space.space_name == "vscode-01"
    assert (holotree_manager._directory / "vscode-01" / "state").read_text(
        "utf-8"
    ) == "created"

    for _ in range(2):
        result: ActionResult[IRobotYamlEnvInfo] = rcc.get_robot_yaml_env_info(
            robot1.robot_yaml,
            robot1.conda_yaml,
            robot1.conda_yaml_contents,
            None,
            holotree_manager=holotree_manager,
        )
        assert result.success
        assert result.result is not None
        robot_yaml_env_info: IRobotYamlEnvInfo = result.result
        assert "PYTHON_EXE" in robot_yaml_env_info.env

        space_info: IRCCSpaceInfo = robot_yaml_env_info.space_info
        with space_info.acquire_lock():
            assert space_info.conda_contents_match(robot1.conda_yaml_contents)

    # Load robot 2 (without any timeout).
    result = rcc.get_robot_yaml_env_info(
        robot2.robot_yaml,
        robot2.conda_yaml,
        robot2.conda_yaml_contents,
        None,
        holotree_manager=holotree_manager,
    )
    assert result.success
    assert result.result is not None
    robot_yaml_env_info = result.result
    assert "PYTHON_EXE" in robot_yaml_env_info.env

    space_info = robot_yaml_env_info.space_info
    with space_info.acquire_lock():
        assert space_info.conda_contents_match(robot2.conda_yaml_contents)

    # Load robot 3 (without any timeout: will pick up the least recently used).
    result = rcc.get_robot_yaml_env_info(
        robot3.robot_yaml,
        robot3.conda_yaml,
        robot3.conda_yaml_contents,
        None,
        holotree_manager=holotree_manager,
    )
    assert result.success
    assert result.result is not None
    robot_yaml_env_info = result.result
    assert "PYTHON_EXE" in robot_yaml_env_info.env

    space_info = robot_yaml_env_info.space_info
    with space_info.acquire_lock():
        assert space_info.conda_contents_match(robot3.conda_yaml_contents)

    # Load robot 3 new comment: should be the same as robot3 as the contents
    # are the same.
    result_robot_3_new_comment = rcc.get_robot_yaml_env_info(
        robot3_new_comment.robot_yaml,
        robot3_new_comment.conda_yaml,
        robot3_new_comment.conda_yaml_contents,
        None,
        holotree_manager=holotree_manager,
    )
    assert result_robot_3_new_comment.success
    assert result_robot_3_new_comment.result is not None

    # i.e.: it must remain the same as the only difference is a comment (which
    # should be removed for the comparison).
    assert (
        result_robot_3_new_comment.result.space_info.space_name == space_info.space_name
    )


def test_get_robot_yaml_environ_not_ok(rcc: IRcc, datadir, holotree_manager):
    # Test what happens when things go don't go as planned (i.e.: an environment
    # cannot be created).
    commands = []

    class RccListener:
        def before_command(self, args: List[str]):
            commands.append(args)

    listener = RccListener()

    rcc.rcc_listeners.append(listener)
    from robocorp_code.protocols import IRobotYamlEnvInfo
    from robocorp_ls_core.protocols import ActionResult

    bad_robot1 = _RobotInfo(datadir, "bad_robot1")
    result: ActionResult[IRobotYamlEnvInfo] = rcc.get_robot_yaml_env_info(
        bad_robot1.robot_yaml,
        bad_robot1.conda_yaml,
        bad_robot1.conda_yaml_contents,
        None,
        holotree_manager=holotree_manager,
    )

    assert not result.success
    assert len(commands) == 1
    command = commands[0]
    del commands[:]
    assert command[1:5] == ["holotree", "variables", "--space", "vscode-01"]

    # Calling it a 2nd time after the first one didn't work shouldn't even
    # call rcc (it'll only be called if the yaml is changed).
    result = rcc.get_robot_yaml_env_info(
        bad_robot1.robot_yaml,
        bad_robot1.conda_yaml,
        bad_robot1.conda_yaml_contents,
        None,
        holotree_manager=holotree_manager,
    )

    assert not result.success
    assert result.message
    assert not commands
    assert "Environment from broken conda.yaml requested" in result.message
