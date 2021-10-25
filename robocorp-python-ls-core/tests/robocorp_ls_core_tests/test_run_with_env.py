def test_create_run_with_env_code(tmpdir):
    import os
    import sys
    from pathlib import Path
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_ls_core import run_with_env

    robocorp_home = tmpdir.join("robohome")
    robo_env = {
        "ROBOCORP_HOME": str(robocorp_home),
        "SOME_KEY": "SOME_VALUE",
    }
    code = run_with_env.create_run_with_env_code(robo_env, sys.executable)
    if sys.platform == "win32":
        shell_script = str(tmpdir.join("my.bat"))
    else:
        shell_script = str(tmpdir.join("my.sh"))

    run_with_env.write_as_script(code, Path(shell_script))

    cmdline = [shell_script, "-c", 'import os;print(os.environ["SOME_KEY"])']

    try:
        output = subprocess.check_output(cmdline, shell=sys.platform == "win32")
        assert b"SOME_VALUE" in output
    except:
        sys.stderr.write(
            "Error when running: %s\n" % (" ".join(str(x) for x in cmdline),)
        )
        raise

    cmdline, env = run_with_env.update_cmdline_and_env(
        ["python", "-c", "foo"], {"some_env_var": "x" * 300}
    )
    assert cmdline[0].endswith((".sh", ".bat"))
    assert cmdline[1:] == ["-c", "foo"]
    assert not env

    os.environ["ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT"] = "0"
    try:
        cmdline, env = run_with_env.update_cmdline_and_env(
            ["python", "-c", "foo"], {"some_env_var": "x" * 300}
        )
        assert cmdline == ["python", "-c", "foo"]
        assert env == {"some_env_var": "x" * 300}
    finally:
        del os.environ["ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT"]
