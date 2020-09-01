from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
import weakref
from robocorp_ls_core.protocols import IConfigProvider
import os.path


def test_resolve_interpreter(
    cases: CasesFixture, config_provider: IConfigProvider, rcc_conda_installed
) -> None:
    from robocorp_ls_core.constants import NULL
    from robocorp_code.plugins.resolve_interpreter import RobocorpResolveInterpreter
    from robocorp_ls_core import uris
    from robocorp_ls_core.pluginmanager import PluginManager
    from robotframework_ls.ep_providers import EPConfigurationProvider
    from robotframework_ls.ep_providers import EPEndPointProvider
    from pathlib import Path
    from robocorp_code.plugins.resolve_interpreter import _CacheInfo

    _CacheInfo._cache_hit_files = 0

    pm = PluginManager()
    pm.set_instance(EPConfigurationProvider, config_provider)
    pm.set_instance(EPEndPointProvider, NULL)

    resolve_interpreter = RobocorpResolveInterpreter(weak_pm=weakref.ref(pm))
    path = cases.get_path(
        "custom_envs/simple-web-scraper/tasks/simple-web-scraper.robot"
    )
    interpreter_info = resolve_interpreter.get_interpreter_info_for_doc_uri(
        uris.from_fs_path(path)
    )
    assert interpreter_info
    assert os.path.exists(interpreter_info.get_python_exe())
    assert interpreter_info.get_environ()
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
    assert _CacheInfo._cache_hit_files == 2
    assert _CacheInfo._cache_hit_interpreter == 1
