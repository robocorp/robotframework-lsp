import pathlib
from typing import Dict, Tuple, List, Optional
import sys
import os


def create_run_with_env_code(
    robo_env: Dict[str, str], base_executable_and_args: List[str]
) -> str:
    """
    :param robo_env:
        This is the environment
        -- if using RCC it's collected through something as:
        rcc holotree variables --space <space_name> -r <robot_path> -e <env_json_path> --json

    :param executable:
        This is the executable which should be called (usually the path to python.exe)
    """
    set_vars = []
    as_dict: Dict[str, str] = {}
    for key, value in robo_env.items():
        if sys.platform == "win32":
            set_vars.append(f"SET {key}={value}")
        else:
            set_vars.append(f"export {key}={value}")
        as_dict[key] = value

    set_vars_as_str = "\n".join(set_vars)
    import subprocess

    if sys.platform == "win32":
        shebang = "@echo off"
        executable_with_args = f"{subprocess.list2cmdline(base_executable_and_args)} %*"
    else:
        shebang = "#!/bin/sh"
        executable_with_args = (
            f'{subprocess.list2cmdline(base_executable_and_args)} "$@"'
        )

    code = f"""{shebang}

{set_vars_as_str}
{executable_with_args}
"""

    return code


def compute_path_for_env(code: str) -> pathlib.Path:
    import tempfile

    temp_dir = os.path.join(tempfile.gettempdir(), "rf-ls-run")

    os.makedirs(temp_dir, exist_ok=True)
    import hashlib

    m = hashlib.sha256()
    m.update(code.encode("utf-8"))

    return pathlib.Path(temp_dir) / (
        "run_env_" + m.hexdigest()[:14] + (".bat" if sys.platform == "win32" else ".sh")
    )


def write_as_script(code: str, script_path: pathlib.Path):
    script_path.write_text(code, "utf-8", "replace")

    if sys.platform != "win32":
        # We need to make it executable...
        import stat

        st = os.stat(str(script_path))
        os.chmod(str(script_path), st.st_mode | stat.S_IEXEC)


def disable_launch_env_script():
    return os.environ.get("ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT", "1").lower() in (
        "0",
        "false",
    )


def _update_command_line_to_write_pid(cmdline: List[str], env: dict, write_pid_to: str):
    from robocorp_ls_core import run_and_save_pid

    new_cmdline = [sys.executable, run_and_save_pid.__file__, write_pid_to] + cmdline
    return new_cmdline, env


def update_cmdline_and_env(
    cmdline: List[str], env: dict, write_pid_to: Optional[str] = None
) -> Tuple[List[str], dict]:
    """
    Ideally only this function is actually used from this module.

    It receives an existing command line and environment and provides a new
    command line and environment to be used depending which should have the
    same effect when running.

    :param write_pid_to: if passed, the launch will be made in a way that
        a wrapper script is used to launch the script and then write the
        pid of the launched executable to the passed file.
    """
    if write_pid_to:
        cmdline, env = _update_command_line_to_write_pid(cmdline, env, write_pid_to)
        embed_args = 3
    else:
        embed_args = 1

    if disable_launch_env_script():
        return cmdline, env

    set_env_and_run_code = create_run_with_env_code(env, cmdline[:embed_args])
    if len(set_env_and_run_code) > 240:
        script_path = compute_path_for_env(set_env_and_run_code)
        write_as_script(set_env_and_run_code, script_path)
        new_cmdline = [str(script_path)] + cmdline[embed_args:]

        return new_cmdline, {}
    return cmdline, env
