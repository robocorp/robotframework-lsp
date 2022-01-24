"""
Note: this code will actually run as a plugin in the RobotFramework Language
Server, or in the Robocorp Code environment, so, we need to be careful on the
imports so that it works on both cases.

Also, the required version must be checked in the client (in case imports or APIs 
change in `robocorp_ls_core` we need a compatible version both on robotframework-ls
as well as robocorp-code).
"""
import os.path
import sys
import itertools

try:
    from robocorp_code.rcc import Rcc  # noqa
except:
    # Automatically add it to the path if executing as a plugin the first time.
    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    import robocorp_code  # @UnusedImport

    from robocorp_code.rcc import Rcc  # noqa


from typing import Optional, Dict, List, Tuple
from collections import namedtuple
import time

from robocorp_ls_core.basic import implements
from robocorp_ls_core.pluginmanager import PluginManager


from robocorp_ls_core.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
    DefaultInterpreterInfo,
)
from robocorp_ls_core import uris
from robocorp_ls_core.robotframework_log import get_logger
from pathlib import Path
import weakref
from robocorp_code.protocols import IRobotYamlEnvInfo


log = get_logger(__name__)


_CachedFileMTimeInfo = namedtuple("_CachedFileMTimeInfo", "st_mtime, st_size, path")

_CachedInterpreterMTime = Tuple[
    Optional[_CachedFileMTimeInfo],
    Optional[_CachedFileMTimeInfo],
    Optional[_CachedFileMTimeInfo],
]


def _get_mtime_cache_info(file_path: Path) -> Optional[_CachedFileMTimeInfo]:
    """
    Cache based on the time/size of a given path.
    """
    try:
        stat = file_path.stat()
        return _CachedFileMTimeInfo(stat.st_mtime, stat.st_size, str(file_path))
    except:
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
            from robocorp_ls_core import yaml_wrapper
            from io import StringIO

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
        from robocorp_ls_core.ep_providers import EPConfigurationProvider

        self._mtime: _CachedInterpreterMTime = self._obtain_mtime(
            robot_yaml_file_info, conda_config_file_info, env_json_path_file_info
        )

        configuration_provider: EPConfigurationProvider = pm[EPConfigurationProvider]
        rcc = Rcc(configuration_provider)
        interpreter_id = str(robot_yaml_file_info.file_path)

        result = rcc.get_robot_yaml_env_info(
            robot_yaml_file_info.file_path,
            conda_config_file_info.file_path,
            conda_config_file_info.contents,
            env_json_path_file_info.file_path
            if env_json_path_file_info is not None
            else None,
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

        from robocorp_ls_core.progress_report import progress_context

        from robocorp_ls_core.ep_providers import EPEndPointProvider

        endpoint = pm[EPEndPointProvider].endpoint

        with progress_context(endpoint, "Obtain env for robot.yaml", dir_cache=None):
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
                    except:
                        log.exception(f"Error making dir: {temp_dir_path}")

                    try:
                        recycle_path: Path = temp_dir_path / "recycle.now"
                        recycle_path.touch()
                    except:
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
            return info

        return self._relocate_robot_root(info)

    def _relocate_robot_root(self, interpreter_info: IInterpreterInfo):
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
            for path in itertools.chain(iter([fs_path]), fs_path.parents):
                robot_yaml: Path = path / "robot.yaml"
                if robot_yaml.exists():
                    break
            else:
                # i.e.: Could not find any robot.yaml in the structure.
                log.debug("Could not find robot.yaml for: %s", fs_path)
                return None

            # Ok, we have the robot_yaml, so, we should be able to run RCC with it.
            try:
                robot_yaml_file_info = _CacheInfo.get_file_info(robot_yaml)
            except:
                log.exception("Error collecting info from: %s", robot_yaml)
                return None

            yaml_contents = robot_yaml_file_info.yaml_contents
            if not isinstance(yaml_contents, dict):
                log.critical(f"Expected dict as root in: {robot_yaml}")
                return None

            conda_config = yaml_contents.get("condaConfigFile")
            conda_config_file_info = None
            env_json_path_file_info = None

            if not conda_config:
                log.critical("Could not find condaConfigFile in %s", robot_yaml)
                return None

            parent: Path = robot_yaml.parent
            conda_config_path = parent / conda_config
            if not conda_config_path.exists():
                log.critical("conda.yaml does not exist in %s", conda_config_path)
                return None

            try:
                conda_config_file_info = _CacheInfo.get_file_info(conda_config_path)
            except:
                log.exception("Error collecting info from: %s", conda_config_path)
                return None

            env_json_path = parent / "devdata" / "env.json"
            if env_json_path.exists():
                try:
                    env_json_path_file_info = _CacheInfo.get_file_info(env_json_path)
                except:
                    log.exception("Error collecting info from: %s", env_json_path)
                    return None

            return _CacheInfo.get_interpreter_info(
                robot_yaml_file_info,
                conda_config_file_info,
                env_json_path_file_info,
                pm,
            )

        except:
            log.exception(f"Error getting interpreter info for: {doc_uri}")
        return None

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


def register_plugins(pm: PluginManager):
    pm.register(
        EPResolveInterpreter,
        RobocorpResolveInterpreter,
        kwargs={"weak_pm": weakref.ref(pm)},
    )
