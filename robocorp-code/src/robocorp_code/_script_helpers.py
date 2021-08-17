import pathlib
from typing import Dict


def convert_robot_env_to_shell(robo_env: Dict[str, str]):
    """
    :param robo_env:
        This is the environment collected from RCC through something
        as: rcc holotree variables --space <space_name> -r <robot_path> -e <env_json_path> --json
    """
    import sys

    set_vars = []
    as_dict: Dict[str, str] = {}
    for key, value in robo_env.items():
        if sys.platform == "win32":
            set_vars.append(f"SET {key}={value}")
        else:
            set_vars.append(f"export {key}={value}")
        as_dict[key] = value

    set_vars_as_str = "\n".join(set_vars)
    python = as_dict.get("PYTHON_EXE", "python")
    if sys.platform == "win32":
        shebang = "@echo off"
        python_with_args = f"{python} %*"
    else:
        shebang = "#!/bin/sh"
        python_with_args = f'{python} "$@"'

    code = f"""{shebang}

{set_vars_as_str}
{python_with_args}
"""

    return code


def write_as_script(code, script_path: pathlib.Path):
    import sys

    script_path.write_text(code, "utf-8", "replace")

    if not sys.platform == "win32":
        # We need to make it executable...
        import os
        import stat

        st = os.stat(str(script_path))
        os.chmod(str(script_path), st.st_mode | stat.S_IEXEC)
