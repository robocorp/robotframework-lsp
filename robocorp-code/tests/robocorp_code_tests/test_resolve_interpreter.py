from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
import weakref
from robocorp_ls_core.protocols import IConfigProvider
import os.path


def test_resolve_interpreter(
    cases: CasesFixture,
    config_provider: IConfigProvider,
    rcc_conda_installed,
    rcc_patch,
) -> None:
    from robocorp_ls_core.constants import NULL
    from robocorp_code.plugins.resolve_interpreter import RobocorpResolveInterpreter
    from robocorp_ls_core import uris
    from robocorp_ls_core.pluginmanager import PluginManager
    from pathlib import Path
    from robocorp_code.plugins.resolve_interpreter import _CacheInfo
    from robocorp_ls_core.ep_providers import EPConfigurationProvider
    from robocorp_ls_core.ep_providers import EPEndPointProvider
    from robocorp_code.holetree_manager import HolotreeManager
    import time

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
