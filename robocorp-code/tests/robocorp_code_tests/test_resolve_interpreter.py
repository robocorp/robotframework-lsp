import io
import os.path
import sys
import weakref

import pytest
from robocorp_ls_core.protocols import IConfigProvider
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture


def test_resolve_interpreter_relocate_robot_root(
    config_provider: IConfigProvider, rcc_conda_installed, datadir
) -> None:
    from pathlib import Path

    from robocorp_ls_core import uris
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.ep_providers import (
        EPConfigurationProvider,
        EPEndPointProvider,
    )
    from robocorp_ls_core.pluginmanager import PluginManager
    from robocorp_ls_core.robotframework_log import configure_logger

    from robocorp_code.plugins.resolve_interpreter import RobocorpResolveInterpreter

    pm = PluginManager()
    pm.set_instance(EPConfigurationProvider, config_provider)
    pm.set_instance(EPEndPointProvider, NULL)

    resolve_interpreter = RobocorpResolveInterpreter(weak_pm=weakref.ref(pm))

    path1 = datadir / "robot3" / "robot.yaml"
    path2 = datadir / "robot3a" / "robot.yaml"

    interpreter_info1 = resolve_interpreter.get_interpreter_info_for_doc_uri(
        uris.from_fs_path(str(path1))
    )
    assert interpreter_info1
    entries = interpreter_info1.get_additional_pythonpath_entries()
    additional_pythonpath_entries = tuple(Path(x) for x in entries)
    assert additional_pythonpath_entries == (datadir / "robot3" / "path1",)

    string_io = io.StringIO()
    with configure_logger("", 0, string_io):
        # i.e.: Don't show the error loading the broken env.json from robot3a.
        interpreter_info2 = resolve_interpreter.get_interpreter_info_for_doc_uri(
            uris.from_fs_path(str(path2))
        )

    assert interpreter_info2
    entries = interpreter_info2.get_additional_pythonpath_entries()
    additional_pythonpath_entries = tuple(Path(x) for x in entries)
    assert additional_pythonpath_entries == (datadir / "robot3a" / "path2",)

    environ1 = interpreter_info1.get_environ()
    environ2 = interpreter_info2.get_environ()
    assert environ1
    assert environ2

    assert "SomeIntVar" not in environ2
    assert environ1["SomeIntVar"] == "1"
    assert environ1["SomeStrVar"] == "1"
    assert environ1["SomeListVar"] == "['1']"

    assert environ1["ROBOT_ROOT"] != environ2["ROBOT_ROOT"]
    for val in environ2:
        assert environ1["ROBOT_ROOT"] not in val
    assert Path(environ1["ROBOT_ROOT"]) == path1.parent
    assert Path(environ2["ROBOT_ROOT"]) == path2.parent

    assert Path(interpreter_info1.get_interpreter_id()) == path1
    assert Path(interpreter_info2.get_interpreter_id()) == path2


def test_resolve_interpreter_environment_config(
    config_provider: IConfigProvider, rcc_conda_installed, datadir
) -> None:
    import subprocess
    import sys

    from robocorp_ls_core import uris
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.ep_providers import (
        EPConfigurationProvider,
        EPEndPointProvider,
    )
    from robocorp_ls_core.pluginmanager import PluginManager

    from robocorp_code.plugins.resolve_interpreter import RobocorpResolveInterpreter

    pm = PluginManager()
    pm.set_instance(EPConfigurationProvider, config_provider)
    pm.set_instance(EPEndPointProvider, NULL)

    resolve_interpreter = RobocorpResolveInterpreter(weak_pm=weakref.ref(pm))

    path1 = datadir / "robot_envconfig" / "robot.yaml"

    interpreter_info1 = resolve_interpreter.get_interpreter_info_for_doc_uri(
        uris.from_fs_path(str(path1))
    )
    assert interpreter_info1
    python_exe = interpreter_info1.get_python_exe()
    output = subprocess.check_output(
        [python_exe, "-c", "import sys;print(sys.version_info[:2])"]
    ).decode("utf-8")
    if sys.platform == "win32":
        assert "(3, 9)" in output

    elif sys.platform == "darwin":
        assert "(3, 10)" in output

    else:
        assert "(3, 11)" in output


def test_fix_entry():
    import sys

    from robocorp_code.plugins.resolve_interpreter import RobocorpResolveInterpreter

    fix_entry = RobocorpResolveInterpreter._fix_entry
    fix_path = RobocorpResolveInterpreter._fix_path

    if sys.platform == "win32":
        entry = "c:\\temp\\foo\\"
        existing_robot_root = "c:\\temp\\foo"
        new_robot_root = "c:\\temp\\bar"

        assert (
            fix_entry(entry, fix_path(existing_robot_root), fix_path(new_robot_root))
            == new_robot_root + "\\"
        )

        entry = "C:\\temp\\foo"
        existing_robot_root = "C:\\temp\\foo"
        new_robot_root = "c:\\temp\\bar"

        assert (
            fix_entry(entry, fix_path(existing_robot_root), fix_path(new_robot_root))
            == new_robot_root
        )

        entry = "c:\\temp\\foo"
        existing_robot_root = "C:\\temp\\foo"
        new_robot_root = "c:\\temp\\bar"

        assert (
            fix_entry(entry, fix_path(existing_robot_root), fix_path(new_robot_root))
            == new_robot_root
        )
    else:
        entry = "/temp/foo"
        existing_robot_root = "/temp/foo"
        new_robot_root = "/temp/bar"

        assert (
            fix_entry(entry, fix_path(existing_robot_root), fix_path(new_robot_root))
            == new_robot_root
        )


def test_resolve_interpreter(
    cases: CasesFixture,
    config_provider: IConfigProvider,
    rcc_conda_installed,
    rcc_patch,
) -> None:
    import time
    from pathlib import Path

    from robocorp_ls_core import uris
    from robocorp_ls_core.constants import NULL
    from robocorp_ls_core.ep_providers import (
        EPConfigurationProvider,
        EPEndPointProvider,
    )
    from robocorp_ls_core.pluginmanager import PluginManager

    from robocorp_code.holetree_manager import HolotreeManager
    from robocorp_code.plugins.resolve_interpreter import (
        RobocorpResolveInterpreter,
        _CacheInfo,
    )

    _CacheInfo._cache_hit_files = 0

    pm = PluginManager()
    pm.set_instance(EPConfigurationProvider, config_provider)
    pm.set_instance(EPEndPointProvider, NULL)

    resolve_interpreter = RobocorpResolveInterpreter(weak_pm=weakref.ref(pm))
    path = cases.get_path(
        "custom_envs/simple-web-scraper/tasks/simple-web-scraper.robot"
    )
    rcc_patch.apply()
    interpreter_info = resolve_interpreter.get_interpreter_info_for_doc_uri(
        uris.from_fs_path(path)
    )
    assert interpreter_info
    assert os.path.exists(interpreter_info.get_python_exe())
    environ = interpreter_info.get_environ()
    assert environ
    assert environ["RPA_SECRET_MANAGER"] == "RPA.Robocloud.Secrets.FileSecrets"
    assert environ["RPA_SECRET_FILE"] == "/Users/<your-username-here>/vault.json"
    additional_pythonpath_entries = interpreter_info.get_additional_pythonpath_entries()
    assert len(additional_pythonpath_entries) == 3
    found = set()
    for v in additional_pythonpath_entries:
        p = Path(v)
        assert p.is_dir()
        found.add(p.name)

    assert found == {"variables", "libraries", "resources"}

    assert _CacheInfo._cache_hit_files == 0
    assert _CacheInfo._cache_hit_interpreter == 0
    interpreter_info = resolve_interpreter.get_interpreter_info_for_doc_uri(
        uris.from_fs_path(path)
    )
    assert interpreter_info
    assert _CacheInfo._cache_hit_files == 3
    assert _CacheInfo._cache_hit_interpreter == 1

    holotree_manager = HolotreeManager(rcc_conda_installed)
    statuses = list(holotree_manager.iter_existing_space_infos())
    if len(statuses) != 1:
        lst = ["Expected a single status. Found:"]
        for status in statuses:
            lst.append(status.pretty())
        raise AssertionError("\n".join(lst))
    status = next(iter(statuses))

    for _ in range(2):
        last_usage = status.load_last_usage(none_if_not_found=True)
        assert last_usage is not None
        time.sleep(0.05)
        interpreter_info = resolve_interpreter.get_interpreter_info_for_doc_uri(
            uris.from_fs_path(path)
        )
        assert interpreter_info
        environ = interpreter_info.get_environ()
        assert environ
        conda_prefix = environ["CONDA_PREFIX"]
        assert os.path.basename(conda_prefix) == "conda_prefix_vscode-01"

        statuses = list(holotree_manager.iter_existing_space_infos())
        assert len(statuses) == 1
        status = next(iter(statuses))
        new_last_usage = status.load_last_usage(none_if_not_found=True)
        assert new_last_usage is not None
        assert last_usage < new_last_usage

    environ = interpreter_info.get_environ()
    assert environ
    temp_dir = Path(environ["TEMP"])
    assert temp_dir.exists()
    recycle_file = temp_dir / "recycle.now"
    assert recycle_file.exists()

    stat = recycle_file.stat()
    time.sleep(1)
    touch_info = getattr(interpreter_info, "__touch_info__")
    touch_info.touch(interpreter_info, force=True)

    stat2 = recycle_file.stat()
    assert stat.st_mtime < stat2.st_mtime


@pytest.mark.skipif(sys.platform != "win32", reason="Expectations require windows.")
def test_match_conda_config_path(datadir):
    from pathlib import Path

    from robocorp_code.plugins.resolve_interpreter import get_conda_config_path

    robot_yaml = Path(datadir / "robot_envconfig" / "robot.yaml")
    parent = robot_yaml.parent

    assert (
        get_conda_config_path(
            parent, robot_yaml, {"condaConfigFile": "conda.yaml"}
        ).name
        == "conda.yaml"
    )

    assert (
        get_conda_config_path(
            parent,
            robot_yaml,
            {
                "condaConfigFile": "conda.yaml",
                "environmentConfigs": ["conda2.yaml"],
            },
        ).name
        == "conda2.yaml"
    )

    assert (
        get_conda_config_path(
            parent,
            robot_yaml,
            {
                "condaConfigFile": "conda.yaml",
                "environmentConfigs": ["conda2_linux.yaml", "conda2.yaml"],
            },
        ).name
        == "conda2.yaml"
    )

    assert (
        get_conda_config_path(
            parent,
            robot_yaml,
            {
                "condaConfigFile": "conda.yaml",
                "environmentConfigs": [
                    "conda.yaml",
                    "environment_windows_amd64_freeze.yaml",
                ],
            },
        ).name
        == "conda.yaml"
    )
