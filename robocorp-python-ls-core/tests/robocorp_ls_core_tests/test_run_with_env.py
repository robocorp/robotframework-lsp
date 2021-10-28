import sys


def test_create_run_with_env_code(tmpdir):
    import os
    from pathlib import Path
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_ls_core import run_with_env
    from robocorp_ls_core import run_and_save_pid

    robocorp_home = tmpdir.join("robohome")
    robo_env = {
        "ROBOCORP_HOME": str(robocorp_home),
        "SOME_KEY": "SOME_VALUE",
    }
    code = run_with_env.create_run_with_env_code(robo_env, [sys.executable])
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
            ["python", "-c", "a=2;b=3;a+b"], {"some_env_var": "x" * 300}
        )
        assert cmdline == ["python", "-c", "a=2;b=3;a+b"]
        assert env == {"some_env_var": "x" * 300}

        write_pid_to = tmpdir.join("some_file")
        cmdline, env = run_with_env.update_cmdline_and_env(
            ["python", "-c", "a=2;b=3;a+b"],
            {"some_env_var": "x" * 300},
            str(write_pid_to),
        )
        assert cmdline == [
            sys.executable,
            run_and_save_pid.__file__,
            str(write_pid_to),
            "python",
            "-c",
            "a=2;b=3;a+b",
        ]
        assert env == {"some_env_var": "x" * 300}

        subprocess.check_call(cmdline)

        assert int(write_pid_to.read_text("utf-8").strip()) > 0

    finally:
        del os.environ["ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT"]


def test_run_and_save_pid_raw(tmpdir):
    from robocorp_ls_core import run_and_save_pid
    import threading
    from robocorp_ls_core.basic import wait_for_condition

    target_file = tmpdir.join("write_pid_to.txt")

    found = []

    def wait_for_pid_in_target_file():
        found.append(run_and_save_pid.wait_for_pid_in_file(target_file))

    threading.Thread(target=wait_for_pid_in_target_file).start()
    run_and_save_pid.main(str(target_file), [sys.executable, "-c", "a=1;b=2;a+b"])

    wait_for_condition(lambda: len(found) > 0)
