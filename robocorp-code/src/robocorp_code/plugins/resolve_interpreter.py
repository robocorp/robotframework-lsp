"""
Note: this code will actually run as a plugin in the RobotFramework Language
Server, or in the Robocorp Code environment, so, we need to be careful on the
imports so that it works on both cases.

Also, the required version must be checked in the client (in case imports or APIs
change in `robocorp_ls_core` we need a compatible version both on robotframework-ls
as well as robocorp-code).
"""

import itertools
import os.path
import sys

from robocorp_ls_core.progress_report import get_current_progress_reporter
from robocorp_ls_core.protocols import RCCActionResult

try:
    from robocorp_code.rcc import Rcc  # noqa
except ImportError:
    # Automatically add it to the path if executing as a plugin the first time.
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    import robocorp_code  # @UnusedImport

    from robocorp_code.rcc import Rcc  # noqa

import time
import weakref
from collections import namedtuple
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from robocorp_ls_core import uris
from robocorp_ls_core.basic import implements
from robocorp_ls_core.ep_resolve_interpreter import (
    DefaultInterpreterInfo,
    EPResolveInterpreter,
    IInterpreterInfo,
)
from robocorp_ls_core.pluginmanager import PluginManager
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.protocols import IRobotYamlEnvInfo

log = get_logger(__name__)


_CachedFileMTimeInfo = namedtuple("_CachedFileMTimeInfo", "st_mtime, st_size, path")

_CachedInterpreterMTime = Tuple[Optional[_CachedFileMTimeInfo], ...]


def _get_mtime_cache_info(file_path: Path) -> Optional[_CachedFileMTimeInfo]:
    """
    Cache based on the time/size of a given path.
    """
    try:
        stat = file_path.stat()
        return _CachedFileMTimeInfo(stat.st_mtime, stat.st_size, str(file_path))
    except Exception:
        # It could be removed in the meanwhile.
        log.exception(f"Unable to get mtime info for: {file_path}")
        return None


class _CachedFileInfo(object):
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.mtime_info: Optional[_CachedFileMTimeInfo] = _get_mtime_cache_info(
            file_path
        )
        self.contents: str = file_path.read_text(encoding="utf-8", errors="replace")
        self._yaml_contents: Optional[dict] = None

    @property
    def yaml_contents(self) -> dict:
        yaml_contents = self._yaml_contents
        if yaml_contents is None:
            from io import StringIO

            from robocorp_ls_core import yaml_wrapper

            s = StringIO(self.contents)
            yaml_contents = self._yaml_contents = yaml_wrapper.load(s)
        return yaml_contents

    def is_cache_valid(self) -> bool:
        return self.mtime_info == _get_mtime_cache_info(self.file_path)


class _CachedInterpreterInfo(object):
    def __init__(
        self,
        robot_yaml_file_info: _CachedFileInfo,
        conda_config_file_info: _CachedFileInfo,
        env_json_path_file_info: Optional[_CachedFileInfo],
        pm: PluginManager,
    ):
        from robocorp_ls_core.ep_providers import (
            EPConfigurationProvider,
            EPEndPointProvider,
        )
        from robocorp_ls_core.lsp import LSPMessages
        from robocorp_ls_core.protocols import IEndPoint

        from robocorp_code.commands import ROBOCORP_SHOW_INTERPRETER_ENV_ERROR

        self._mtime: _CachedInterpreterMTime = self._obtain_mtime(
            robot_yaml_file_info, conda_config_file_info, env_json_path_file_info
        )

        configuration_provider: EPConfigurationProvider = pm[EPConfigurationProvider]
        endpoint_provider: EPEndPointProvider = pm[EPEndPointProvider]
        rcc = Rcc(configuration_provider)
        interpreter_id = str(robot_yaml_file_info.file_path)
        progress_reporter = get_current_progress_reporter()

        def on_env_creation_error(result: RCCActionResult):
            import tempfile

            # Note: called only on environment creation (not on all failures).
            endpoint: IEndPoint = endpoint_provider.endpoint
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".log", prefix="robocorp_code_env_error_"
            ) as f:
                if progress_reporter is not None and progress_reporter.cancelled:
                    file_contents = f"""
Robocorp Code: Environment creation cancelled
===============================================

The process to create the the environment for:

"{conda_config_file_info.file_path}"

was cancelled.

In this case, open "{conda_config_file_info.file_path}"
and update the dependencies accordingly (after saving
the environment will be automatically updated).

If the environment file should be already correct, chose one of the options below:

- Retry restarting VSCode using the command:

  "Developer: Reload Window"

- Clear all environments and restart Robocorp Code (advised if you suspect
  that some environment was partially created and is corrupt):

  "Robocorp: Clear Robocorp (RCC) environments and restart Robocorp Code"

Full error message
====================

{result.message}
"""

                else:
                    file_contents = f"""
Robocorp Code: Unable to create environment
=============================================

There was an error creating the environment for:

"{conda_config_file_info.file_path}"

The full output to diagnose the issue is shown below.
The most common reasons and fixes for this failure are:

1. Dependencies specified are not resolvable.

    In this case, open "{conda_config_file_info.file_path}"
    and update the dependencies accordingly (after saving
    the environment will be automatically updated).

2. There's some intermittent network failure or some active firewall.

    In this case, fix the network connectivity issue and chose one of the options below:

    - Retry restarting VSCode using the command:

      "Developer: Reload Window"

    - Clear all environments and restart Robocorp code (advised if you suspect
      that some environment was partially created and is corrupt):

      "Robocorp: Clear Robocorp (RCC) environments and restart Robocorp Code"

If you still can't get it to work, please submit an issue to Robocorp using the command:

  "Robocorp: Submit issue to Robocorp".


Full error message
====================

{result.message}
"""
                f.write(file_contents.encode("utf-8"))
                message = result.message
                if message:
                    f.write(message.encode("utf-8"))

            lsp_messages = LSPMessages(endpoint)
            lsp_messages.execute_workspace_command(
                ROBOCORP_SHOW_INTERPRETER_ENV_ERROR,
                {
                    "fileWithError": str(f.name),
                    "condaYaml": str(conda_config_file_info.file_path),
                },
            )

        result = rcc.get_robot_yaml_env_info(
            robot_yaml_file_info.file_path,
            conda_config_file_info.file_path,
            conda_config_file_info.contents,
            env_json_path_file_info.file_path
            if env_json_path_file_info is not None
            else None,
            on_env_creation_error=on_env_creation_error,
        )
        if not result.success:
            raise RuntimeError(f"Unable to get env details. Error: {result.message}.")

        robot_yaml_env_info: Optional[IRobotYamlEnvInfo] = result.result
        if robot_yaml_env_info is None:
            raise RuntimeError(f"Unable to get env details. Error: {result.message}.")

        environ = robot_yaml_env_info.env

        root = str(robot_yaml_file_info.file_path.parent)
        pythonpath_lst = robot_yaml_file_info.yaml_contents.get("PYTHONPATH", [])
        additional_pythonpath_entries: List[str] = []
        if isinstance(pythonpath_lst, list):
            for v in pythonpath_lst:
                additional_pythonpath_entries.append(os.path.join(root, str(v)))

        self.robot_yaml_env_info: IRobotYamlEnvInfo = robot_yaml_env_info
        self.info: IInterpreterInfo = DefaultInterpreterInfo(
            interpreter_id,
            environ["PYTHON_EXE"],
            environ,
            additional_pythonpath_entries,
        )

    def _obtain_mtime(
        self,
        robot_yaml_file_info: _CachedFileInfo,
        conda_config_file_info: Optional[_CachedFileInfo],
        env_json_path_file_info: Optional[_CachedFileInfo],
    ) -> _CachedInterpreterMTime:
        return (
            robot_yaml_file_info.mtime_info,
            conda_config_file_info.mtime_info if conda_config_file_info else None,
            env_json_path_file_info.mtime_info if env_json_path_file_info else None,
        )

    def is_cache_valid(
        self,
        robot_yaml_file_info: _CachedFileInfo,
        conda_config_file_info: Optional[_CachedFileInfo],
        env_json_path_file_info: Optional[_CachedFileInfo],
    ) -> bool:
        return self._mtime == self._obtain_mtime(
            robot_yaml_file_info, conda_config_file_info, env_json_path_file_info
        )


class _CacheInfo(object):
    """
    As a new instance of the RobocorpResolveInterpreter is created for each call,
    we need to store cached info outside it.
    """

    _cached_file_info: Dict[Path, _CachedFileInfo] = {}
    _cached_interpreter_info: Dict[Path, _CachedInterpreterInfo] = {}
    _cache_hit_files = 0  # Just for testing
    _cache_hit_interpreter = 0  # Just for testing

    @classmethod
    def clear_cache(cls):
        cls._cached_file_info.clear()
        cls._cached_interpreter_info.clear()
        cls._cache_hit_files = 0  # Just for testing
        cls._cache_hit_interpreter = 0  # Just for testing

    @classmethod
    def get_file_info(cls, file_path: Path) -> _CachedFileInfo:
        file_info = cls._cached_file_info.get(file_path)
        if file_info is not None and file_info.is_cache_valid():
            cls._cache_hit_files += 1
            return file_info

        # If it got here, it's not cached or the cache doesn't match.
        file_info = _CachedFileInfo(file_path)
        cls._cached_file_info[file_path] = file_info
        return file_info

    @classmethod
    def get_interpreter_info(
        cls,
        robot_yaml_file_info: _CachedFileInfo,
        conda_config_file_info: _CachedFileInfo,
        env_json_path_file_info: Optional[_CachedFileInfo],
        pm: PluginManager,
    ) -> IInterpreterInfo:
        interpreter_info: Optional[
            _CachedInterpreterInfo
        ] = cls._cached_interpreter_info.get(robot_yaml_file_info.file_path)
        if interpreter_info is not None and interpreter_info.is_cache_valid(
            robot_yaml_file_info, conda_config_file_info, env_json_path_file_info
        ):
            space_info = interpreter_info.robot_yaml_env_info.space_info
            environ = interpreter_info.info.get_environ()
            if environ is not None:
                ok = True
                conda_prefix = environ.get("CONDA_PREFIX")
                if conda_prefix is None:
                    log.critical(
                        f"Expected CONDA_PREFIX to be available in the environ. Found: {environ}."
                    )
                    ok = False
                else:
                    conda_id = Path(conda_prefix) / "identity.yaml"
                    space_info = interpreter_info.robot_yaml_env_info.space_info
                    if not space_info.matches_conda_identity_yaml(conda_id):
                        log.critical(
                            f"The conda contents in: {conda_id} no longer match the contents from {conda_config_file_info.file_path}."
                        )
                        ok = False

                if ok:
                    space_info.update_last_usage()
                    _CacheInfo._cache_hit_interpreter += 1
                    _touch_temp(interpreter_info.info)
                    return interpreter_info.info

        from robocorp_ls_core.ep_providers import EPEndPointProvider
        from robocorp_ls_core.progress_report import progress_context

        endpoint = pm[EPEndPointProvider].endpoint

        basename = os.path.basename(robot_yaml_file_info.file_path)
        with progress_context(
            endpoint, f"Obtain env for {basename}", dir_cache=None, cancellable=True
        ):
            # If it got here, it's not cached or the cache doesn't match.
            # This may take a while...
            interpreter_info = cls._cached_interpreter_info[
                robot_yaml_file_info.file_path
            ] = _CachedInterpreterInfo(
                robot_yaml_file_info,
                conda_config_file_info,
                env_json_path_file_info,
                pm,
            )

            _touch_temp(interpreter_info.info)
            return interpreter_info.info


class _TouchInfo(object):
    def __init__(self):
        self._last_touch = 0

    def touch(self, info: IInterpreterInfo, force: bool = False):
        curr_time = time.time()
        diff = curr_time - self._last_touch

        one_hour_in_seconds = 60 * 60

        if diff > one_hour_in_seconds or force:  # i.e.: verify it at most once/hour.
            self._last_touch = curr_time
            environ = info.get_environ()
            if environ:
                temp_dir: Optional[str] = environ.get("TEMP")
                if temp_dir:
                    temp_dir_path = Path(temp_dir)
                    try:
                        temp_dir_path.mkdir(exist_ok=True)
                    except Exception:
                        log.exception(f"Error making dir: {temp_dir_path}")

                    try:
                        recycle_path: Path = temp_dir_path / "recycle.now"
                        recycle_path.touch()
                    except Exception:
                        log.exception(f"Error touching: {recycle_path}")


def _touch_temp(info: IInterpreterInfo):
    # When reusing some space, account that the cached TEMP folder we have
    # may be removed and refresh its time accordingly.

    # Dynamically assign a _TouchInfo to this instance to manage doing the actual touch.
    touch_info = getattr(info, "__touch_info__", None)
    if touch_info is None:
        touch_info = _TouchInfo()
        setattr(info, "__touch_info__", touch_info)
    touch_info.touch(info)


class _PackageYamlCachedInfo:
    def __init__(
        self,
        robot_yaml: Path,
        conda_yaml: Path,
        package_yaml_file_info: _CachedFileInfo,
        cached_package_mtime_info: Optional[_CachedFileMTimeInfo],
        cached_package_contents: Optional[str],
    ):
        self.robot_yaml = robot_yaml
        self.conda_yaml = conda_yaml
        self.package_yaml_file_info: _CachedFileInfo = package_yaml_file_info
        self.cached_package_mtime_info = cached_package_mtime_info
        self.cached_package_contents = cached_package_contents

    def is_valid(self, package_yaml_file_info: _CachedFileInfo) -> bool:
        return (
            package_yaml_file_info.mtime_info == self.cached_package_mtime_info
            and package_yaml_file_info.contents == self.cached_package_contents
        )

    def get_cached(self) -> Tuple[Path, Path]:
        return self.robot_yaml, self.conda_yaml


class _CachePackage:
    def __init__(self) -> None:
        self._cache: Dict[Path, "_PackageYamlCachedInfo"] = {}
        self._hits = 0

    def get(self, key) -> Optional["_PackageYamlCachedInfo"]:
        ret = self._cache.get(key)
        if ret is not None:
            self._hits += 1
        return ret

    def __setitem__(self, key: Path, val: "_PackageYamlCachedInfo"):
        self._cache[key] = val

    def clear(self):
        self._cache.clear()
        self._hits = 0


_cache_package = _CachePackage()


class RobocorpResolveInterpreter(object):
    """
    Resolves the interpreter based on the robot.yaml found.
    """

    def __init__(self, weak_pm: "weakref.ReferenceType[PluginManager]"):
        self._pm = weak_pm

    @implements(EPResolveInterpreter.get_interpreter_info_for_doc_uri)
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        info = self._compute_base_interpreter_info_for_doc_uri(doc_uri)
        if info is None:
            return None
        return self._relocate_robot_root(info)

    def _relocate_robot_root(
        self, interpreter_info: IInterpreterInfo
    ) -> Optional[IInterpreterInfo]:
        environ = interpreter_info.get_environ()
        if not environ:
            return interpreter_info

        robot_yaml = interpreter_info.get_interpreter_id()

        existing_robot_root = environ.get("ROBOT_ROOT")
        if existing_robot_root is None:
            return interpreter_info

        new_robot_root = self._fix_path(os.path.dirname(robot_yaml))
        existing_robot_root = self._fix_path(existing_robot_root)

        if new_robot_root.endswith(("/", "\\")):
            new_robot_root = new_robot_root[:-1]

        if existing_robot_root.endswith(("/", "\\")):
            existing_robot_root = existing_robot_root[:-1]

        fix_entry = self._fix_entry

        new_environ = {}
        for key, val in environ.items():
            new_environ[key] = os.pathsep.join(
                fix_entry(entry, existing_robot_root, new_robot_root)
                for entry in val.split(os.pathsep)
            )

        # Note: these should already be correct.
        # new_additional_pythonpath_entries: List[str] = []
        # for entry in interpreter_info.get_additional_pythonpath_entries():
        #     new_additional_pythonpath_entries.append(
        #         fix_entry(entry, existing_robot_root, new_robot_root)
        #     )

        return DefaultInterpreterInfo(
            robot_yaml,
            interpreter_info.get_python_exe(),
            new_environ,
            interpreter_info.get_additional_pythonpath_entries(),
        )

    @classmethod
    def _fix_entry(cls, entry: str, existing_robot_root: str, new_robot_root: str):
        if existing_robot_root == new_robot_root:
            # Nothing to do.
            return entry
        entry = cls._fix_path(entry)
        return entry.replace(existing_robot_root, new_robot_root)

    @classmethod
    def _fix_path(cls, path: str) -> str:
        if sys.platform == "win32":
            # On windows we need to fix the drive letter as we want to
            # replace 'C:' and 'c:'.
            if len(path) > 2 and path[1] == ":":
                drive_letter = path[0]
                if drive_letter.lower() == drive_letter:
                    return path

                return drive_letter.lower() + path[1:]

        return path

    def _generate_robot_and_conda_from_package_yaml(
        self,
        package_yaml_file_info: _CachedFileInfo,
        cache: _CachePackage = _cache_package,
    ) -> Optional[Tuple[Path, Path]]:
        import yaml
        from robocorp_ls_core.ep_providers import EPConfigurationProvider

        from robocorp_code.vendored_deps.action_package_handling import (
            create_conda_contents_from_package_yaml_contents,
            create_hash,
        )

        cached_info: Optional[_PackageYamlCachedInfo] = cache.get(
            package_yaml_file_info.file_path
        )
        package_mtime_info: Optional[
            _CachedFileMTimeInfo
        ] = package_yaml_file_info.mtime_info
        if package_mtime_info is None:
            log.critical(
                "Unable to get mtime info from: %s", package_yaml_file_info.file_path
            )
            return None

        if cached_info is not None:
            if cached_info.is_valid(package_yaml_file_info):
                return cached_info.get_cached()
        # If it got here, it's not cached or the cache is invalid.
        # Let's compute it now.

        pm = self._pm()
        assert pm is not None

        configuration_provider: EPConfigurationProvider = pm[EPConfigurationProvider]
        rcc = Rcc(configuration_provider)

        datadir = rcc.get_robocorp_code_datadir()
        datadir.mkdir(parents=True, exist_ok=True)

        conda_contents: dict = create_conda_contents_from_package_yaml_contents(
            package_yaml_file_info.file_path,
            package_yaml_file_info.yaml_contents,
        )

        conda_as_str = yaml.dump(conda_contents)
        conda_hash = create_hash(conda_as_str)[:12]

        use_dir = datadir / "pkg-to-conda" / conda_hash

        # Note: even if it exists, override (that should be Ok
        # and if there's an error it'll be fixed).
        use_dir.mkdir(parents=True, exist_ok=True)
        conda_yaml = use_dir / "conda.yaml"
        conda_yaml.write_text(conda_as_str, "utf-8")

        robot_yaml = use_dir / "robot.yaml"
        robot_yaml.write_text(
            """
environmentConfigs:
  - environment_windows_amd64_freeze.yaml
  - environment_linux_amd64_freeze.yaml
  - environment_darwin_amd64_freeze.yaml
  - conda.yaml
""",
            "utf-8",
        )

        # Mark when it was last used (we should remove things unused for
        # a long time).
        last_use: Path = use_dir / "last-use.touch"
        last_use.touch()

        original_package_yaml = use_dir / "package.yaml"
        original_package_yaml.write_text(package_yaml_file_info.contents, "utf-8")

        cached_info = _PackageYamlCachedInfo(
            robot_yaml,
            conda_yaml,
            package_yaml_file_info,
            cached_package_mtime_info=package_mtime_info,
            cached_package_contents=package_yaml_file_info.contents,
        )
        cache[package_yaml_file_info.file_path] = cached_info
        return cached_info.get_cached()

    def _compute_base_interpreter_info_for_doc_uri(
        self, doc_uri
    ) -> Optional[IInterpreterInfo]:
        try:
            pm = self._pm()
            if pm is None:
                log.critical("Did not expect PluginManager to be None at this point.")
                return None

            from robocorp_ls_core.ep_providers import (
                EPConfigurationProvider,
                EPEndPointProvider,
            )

            # Check that our requirements are there.
            pm[EPConfigurationProvider]
            pm[EPEndPointProvider]

            fs_path = Path(uris.to_fs_path(doc_uri))
            # Note: there's a use-case where a directory may be passed to
            # compute as the doc_uri, so, handle that too.
            found_package_yaml = False

            for path in itertools.chain(iter([fs_path]), fs_path.parents):
                # Give higher priority to package.yaml (in case conda.yaml became
                # package.yaml but robot.yaml is still lingering around).
                package_yaml: Path = path / "package.yaml"
                if package_yaml.exists():
                    found_package_yaml = True
                    break

                robot_yaml: Path = path / "robot.yaml"
                if robot_yaml.exists():
                    break

            else:
                # i.e.: Could not find any package.yaml nor robot.yaml in the structure.
                log.debug("Could not find package.yaml nor robot.yaml for: %s", fs_path)
                return None

            if found_package_yaml:
                # RCC does not have a way to consume the package.yaml directly,
                # so, what we do at this point is generate the `robot.yaml`
                # and `conda.yaml`.
                try:
                    package_yaml_file_info = _CacheInfo.get_file_info(package_yaml)
                    robot_and_conda = self._generate_robot_and_conda_from_package_yaml(
                        package_yaml_file_info
                    )
                    if robot_and_conda is None:
                        return None

                    robot_yaml, _conda_yaml = robot_and_conda
                except Exception:
                    log.exception(
                        "Unable to generate environment from: %s", package_yaml
                    )
                    return None

            # Ok, we have the robot_yaml, so, we should be able to run RCC with it.
            try:
                robot_yaml_file_info = _CacheInfo.get_file_info(robot_yaml)
            except Exception:
                log.exception("Error collecting info from: %s", robot_yaml)
                return None

            yaml_contents = robot_yaml_file_info.yaml_contents
            if not isinstance(yaml_contents, dict):
                log.critical(f"Expected dict as root in: {robot_yaml}")
                return None

            parent: Path = robot_yaml.parent
            conda_config_path = get_conda_config_path(parent, robot_yaml, yaml_contents)
            if not conda_config_path:
                return None

            try:
                conda_config_file_info = _CacheInfo.get_file_info(conda_config_path)
            except Exception:
                log.exception("Error collecting info from: %s", conda_config_path)
                return None

            env_json_path = parent / "devdata" / "env.json"
            env_json_path_file_info = None
            if env_json_path.exists():
                try:
                    env_json_path_file_info = _CacheInfo.get_file_info(env_json_path)
                except Exception:
                    log.exception("Error collecting info from: %s", env_json_path)
                    return None

            return _CacheInfo.get_interpreter_info(
                robot_yaml_file_info,
                conda_config_file_info,
                env_json_path_file_info,
                pm,
            )
        except Exception as e:
            log.exception(f"Error getting interpreter info for: {doc_uri}: {e}")
        return None

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


def get_conda_config_path(
    parent: Path, robot_yaml: Path, yaml_contents: dict
) -> Optional[Path]:
    environments_config = yaml_contents.get("environmentConfigs")
    if environments_config:
        if isinstance(environments_config, (tuple, list)):
            # The arch is tricky. For instance, in Mac, the user would like to
            # have the target in aarch64 or amd64? It may not match the flavor
            # of the binary we're in and not even the processor... Should
            # this be specified in the robot? For now we simply don't filter
            # through the arch.

            if sys.platform == "win32":
                plat = "windows"

            elif sys.platform == "darwin":
                plat = "darwin"

            else:
                plat = "linux"

            for conda_env_conf in environments_config:
                if plat not in conda_env_conf:
                    import re

                    m = re.match(".*(windows|darwin|linux).*", conda_env_conf)
                    if m:
                        continue

                    # It doesn't have any platform to match (so, it matches any platform).

                p = parent / conda_env_conf
                try:
                    if not p.exists():
                        continue

                    return p
                except Exception:
                    log.exception("Error collecting info from: %s", p)

    conda_config = yaml_contents.get("condaConfigFile")

    if not conda_config:
        log.critical(
            "Dif not find env match in environmentConfigs/condaConfigFile in %s",
            robot_yaml,
        )
        return None

    conda_config_path = parent / conda_config
    if not conda_config_path.exists():
        log.critical(
            f"{conda_config} (defined from condaConfigFile) does not exist in %s",
            conda_config_path,
        )
        return None

    return conda_config_path


def register_plugins(pm: PluginManager):
    pm.register(
        EPResolveInterpreter,
        RobocorpResolveInterpreter,
        kwargs={"weak_pm": weakref.ref(pm)},
    )
