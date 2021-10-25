import pathlib
from typing import Dict, Tuple, List
import sys
import os


def create_run_with_env_code(robo_env: Dict[str, str], executable: str) -> str:
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
    if sys.platform == "win32":
        shebang = "@echo off"
        executable_with_args = f"{executable} %*"
    else:
        shebang = "#!/bin/sh"
        executable_with_args = f'{executable} "$@"'

    code = f"""{shebang}

{set_vars_as_str}
{executable_with_args}
"""

    return code


def compute_path_for_env(code: str, executable: str) -> pathlib.Path:
    import tempfile

    temp_dir = os.path.join(tempfile.gettempdir(), "rf-ls-run")

    os.makedirs(temp_dir, exist_ok=True)
    import hashlib

    m = hashlib.sha256()
    m.update(code.encode("utf-8"))
    m.update(executable.encode("utf-8"))

    return pathlib.Path(temp_dir) / (
        "run_env_" + m.hexdigest()[:14] + (".bat" if sys.platform == "win32" else ".sh")
    )


def write_as_script(code: str, script_path: pathlib.Path):
    script_path.write_text(code, "utf-8", "replace")

    if not sys.platform == "win32":
        # We need to make it executable...
        import stat

        st = os.stat(str(script_path))
        os.chmod(str(script_path), st.st_mode | stat.S_IEXEC)


def update_cmdline_and_env(cmdline: List[str], env: dict) -> Tuple[List[str], dict]:
    """
    Ideally only this function is actually used from this module.

    It receives an existing command line and environment and provides a new
    command line and environment to be used depending which should have the
    same effect when running.
    """
    if os.environ.get("ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT", "1").lower() in (
        "0",
        "false",
    ):
        return cmdline, env

    set_env_and_run_code = create_run_with_env_code(env, cmdline[0])
    if len(set_env_and_run_code) > 240:
        script_path = compute_path_for_env(set_env_and_run_code, cmdline[0])
        write_as_script(set_env_and_run_code, script_path)
        new_cmdline = [str(script_path)] + cmdline[1:]

        return new_cmdline, {}
    return cmdline, env
