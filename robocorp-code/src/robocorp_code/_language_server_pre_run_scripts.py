import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from robocorp_code import commands
from robocorp_ls_core.command_dispatcher import _SubCommandDispatcher
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.subprocess_wrapper import LaunchActionResultDict

pre_run_scripts_command_dispatcher = _SubCommandDispatcher("_pre_run_scripts")


log = get_logger(__name__)


@dataclass
class _PreRunScriptsInfo:
    robot_yaml: Path
    pre_run_scripts: List[str]


class _PreRunScripts:
    def __init__(self, base_command_dispatcher):
        base_command_dispatcher.register_sub_command_dispatcher(
            pre_run_scripts_command_dispatcher
        )

    def _get_pre_run_scripts(self, robot) -> Optional[_PreRunScriptsInfo]:
        from robocorp_code.find_robot_yaml import find_robot_yaml_path_from_path
        from robocorp_ls_core import yaml_wrapper

        path = Path(robot)
        try:
            stat = path.stat()
        except Exception:
            log.exception(f"Expected {path} to exist.")
            return None

        robot_yaml: Optional[Path] = find_robot_yaml_path_from_path(path, stat)

        if not robot_yaml:
            return None

        try:
            with open(robot_yaml, "r") as stream:
                contents = yaml_wrapper.load(stream)
        except Exception:
            log.exception(f"Error loading: {robot_yaml}")
            return None

        try:
            pre_run_scripts = contents.get("preRunScripts")
            if pre_run_scripts:
                pre_run_scripts = list(self._filter_pre_run_scripts(pre_run_scripts))
                if pre_run_scripts:
                    return _PreRunScriptsInfo(
                        pre_run_scripts=pre_run_scripts,
                        robot_yaml=robot_yaml,
                    )
        except Exception:
            log.exception(f"Error detecting preRunScripts: {robot_yaml}")
            return None

        return None

    def _filter_pre_run_scripts(self, pre_run_scripts: List[str]) -> Iterable[str]:
        import platform

        # See docs: https://github.com/robocorp/rcc/blob/master/docs/recipes.md#what-are-prerunscripts

        # If script names contains some of "amd64", "arm64", "darwin", "windows"
        # and/or "linux" words (like script_for_amd64_linux.sh) then other
        # architectures and operating systems will skip those scripts, and only
        # amd64 linux systems will execute them.

        aarch = platform.machine().lower()  # will give us amd64/arm64.
        if sys.platform == "win32":
            plat = "windows"

        elif sys.platform == "darwin":
            plat = "darwin"

        else:
            plat = "linux"

        invalid_platforms = [x for x in ["windows", "darwin", "linux"] if x != plat]
        invalid_aarch = [x for x in ["arm64", "amd64"] if x != aarch]

        for f in pre_run_scripts:
            f = f.lower()

            invalid = False
            for check_plat in invalid_platforms:
                if check_plat in f:
                    # Can't add this one.
                    invalid = True
                    continue

            if invalid:
                continue

            for check_aarch in invalid_aarch:
                if check_aarch in f:
                    # Can't add this one.
                    invalid = True
                    continue

            if invalid:
                continue

            # Ok, exclusions not found: use it.
            yield f

    @pre_run_scripts_command_dispatcher(commands.ROBOCORP_HAS_PRE_RUN_SCRIPTS_INTERNAL)
    def _has_pre_run_scripts_internal(self, params: dict) -> bool:
        return bool(self._get_pre_run_scripts(params["robot"]))

    @pre_run_scripts_command_dispatcher(commands.ROBOCORP_RUN_PRE_RUN_SCRIPTS_INTERNAL)
    def _run_pre_run_scripts_internal(
        self, params: dict
    ) -> Optional[LaunchActionResultDict]:
        import shlex
        from robocorp_ls_core.subprocess_wrapper import launch

        pre_run_scripts = self._get_pre_run_scripts(params["robot"])
        if pre_run_scripts:
            env = params["env"]
            cwd = str(pre_run_scripts.robot_yaml.parent)

            for script in pre_run_scripts.pre_run_scripts:
                sys.stderr.write(
                    f"Running preRunScript: {script} from {str(pre_run_scripts.robot_yaml)}\n"
                )
                command = shlex.split(script, posix=True)
                if command:
                    result = launch(
                        command,
                        timeout=60 * 60,  # 1 hour timeout
                        cwd=cwd,
                        show_interactive_output=True,
                        env=env,
                        shell=command[0].endswith((".bat", ".sh", ".py")),
                    )
                    if not result.success:
                        return result.as_dict()
        return None
