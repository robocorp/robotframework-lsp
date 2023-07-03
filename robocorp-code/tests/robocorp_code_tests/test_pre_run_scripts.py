from robocorp_ls_core.constants import NULL
from pathlib import Path
import sys
import os


def test_run_pre_run_scripts_skip_plat(tmpdir):
    if sys.platform == "win32":
        all_skipped_content = """
preRunScripts: [linux_call.sh, darwin_call.sh]
"""
    elif sys.platform == "darwin":
        all_skipped_content = """
preRunScripts: [linux_call.sh, windows_call.sh]
"""
    else:
        all_skipped_content = """
preRunScripts: [darwin_call.sh, windows_call.sh]
"""

    robot = Path(str(tmpdir)) / "robot.yaml"
    robot.write_text(all_skipped_content)
    from robocorp_code._language_server_pre_run_scripts import _PreRunScripts

    pre_run_scripts = _PreRunScripts(NULL)
    assert not pre_run_scripts._has_pre_run_scripts_internal(
        params={"robot": str(tmpdir)}
    )


def test_run_pre_run_scripts(tmpdir, capsys):
    if sys.platform == "win32":
        content = """
preRunScripts: [windows_call.bat]
"""
        (tmpdir / "windows_call.bat").write_text(
            """
echo OFF
echo WORKED!""",
            "utf-8",
        )
    else:
        content = """
preRunScripts: ["./call.sh"]
"""
        (tmpdir / "call.sh").write_text(
            """
#! /bin/sh -
echo WORKED!
""",
            "utf-8",
        )
        current_permissions = os.stat((tmpdir / "call.sh")).st_mode

        # Make executable
        new_permissions = current_permissions | 0o111
        os.chmod(str((tmpdir / "call.sh")), new_permissions)

    robot = Path(str(tmpdir)) / "robot.yaml"
    robot.write_text(content)
    from robocorp_code._language_server_pre_run_scripts import _PreRunScripts

    pre_run_scripts = _PreRunScripts(NULL)
    assert pre_run_scripts._has_pre_run_scripts_internal(params={"robot": str(tmpdir)})

    result = pre_run_scripts._run_pre_run_scripts_internal(
        params={"robot": str(tmpdir), "env": os.environ.copy()}
    )
    assert result is None
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("WORKED!") == 1


def test_run_pre_run_scripts_bad(tmpdir, capsys):
    content = """
preRunScripts: ['python -m import sys;print(sys.executable)']
"""

    robot = Path(str(tmpdir)) / "robot.yaml"
    robot.write_text(content)
    from robocorp_code._language_server_pre_run_scripts import _PreRunScripts

    pre_run_scripts = _PreRunScripts(NULL)
    assert pre_run_scripts._has_pre_run_scripts_internal(params={"robot": str(tmpdir)})

    result = pre_run_scripts._run_pre_run_scripts_internal(
        params={"robot": str(tmpdir), "env": os.environ.copy()}
    )
    assert result
    assert not result["success"]
