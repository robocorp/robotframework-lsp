import sys
import pathlib


def test_create_run_with_env_code(tmpdir):
    import os
    from pathlib import Path
    from robocorp_ls_core.subprocess_wrapper import subprocess
    from robocorp_ls_core import run_with_env
    from robocorp_ls_core import run_and_save_pid

    robocorp_home = tmpdir.join("robohome")
    robo_env = {
        "ROBOCORP_HOME": str(robocorp_home),
        "SOME_KEY": 'VAL\nWITH\n^NEWLINE^%a% & < > | echo a ^> b ^& !some!another " ra"("`\'',
    }
    code = run_with_env.create_run_with_env_code(robo_env, [sys.executable])
    if sys.platform == "win32":
        shell_script = str(tmpdir.join("my.bat"))
    else:
        shell_script = str(tmpdir.join("my.sh"))

    run_with_env.write_as_script(code, Path(shell_script))

    cmdline = [shell_script, "-c", 'import os;print(repr(os.environ["SOME_KEY"]))']

    try:
        output = subprocess.check_output(cmdline, shell=sys.platform == "win32")
        assert (
            b'\'VAL\\nWITH\\n^NEWLINE^%a% & < > | echo a ^> b ^& !some!another " ra"("`\\\''
            in output
        )
    except:
        sys.stderr.write(
            "Error when running: %s\n" % (" ".join(str(x) for x in cmdline),)
        )
        raise

    cmdline, env = run_with_env.update_cmdline_and_env(
        [sys.executable, "-c", "foo"], {"some_env_var": "x" * 300}
    )
    assert cmdline[0].endswith((".sh", ".bat"))
    assert cmdline[1:] == ["-c", "foo"]
    assert not env

    os.environ["ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT"] = "0"
    try:
        cmdline, env = run_with_env.update_cmdline_and_env(
            [sys.executable, "-c", "a=2;b=3;a+b"], {"some_env_var": "x" * 300}
        )
        assert cmdline == [sys.executable, "-c", "a=2;b=3;a+b"]
        assert env == {"some_env_var": "x" * 300}

        write_pid_to = tmpdir.join("some_file")
        cmdline, env = run_with_env.update_cmdline_and_env(
            [sys.executable, "-c", "a=2;b=3;a+b"],
            {"some_env_var": "x" * 300},
            str(write_pid_to),
        )
        assert cmdline == [
            sys.executable,
            run_and_save_pid.__file__,
            str(write_pid_to),
            sys.executable,
            "-c",
            "a=2;b=3;a+b",
        ]
        assert env == {"some_env_var": "x" * 300}

        subprocess.check_call(cmdline)

        assert int(write_pid_to.read_text("utf-8").strip()) > 0

    finally:
        del os.environ["ROBOTFRAMEWORK_LS_LAUNCH_ENV_SCRIPT"]


def test_delete_old(tmpdir):
    from robocorp_ls_core.run_with_env import _compute_path_for_env
    from robocorp_ls_core.run_with_env import _delete_in_thread
    import datetime
    import os
    import time

    base_dir = str(tmpdir.join("run"))
    f0 = pathlib.Path(_compute_path_for_env(base_dir))
    f1 = pathlib.Path(_compute_path_for_env(base_dir))

    f0.write_text("f0", "utf-8")
    f1.write_text("f1", "utf-8")

    _delete_in_thread(base_dir).join()

    base_dir_as_path = pathlib.Path(base_dir)
    assert len(list(base_dir_as_path.iterdir())) == 2

    # Change the file mtime so that it's considered old.
    date = datetime.datetime.now()
    date = date - datetime.timedelta(days=2.1)
    modTime = time.mktime(date.timetuple())
    os.utime(str(f0), (modTime, modTime))

    _delete_in_thread(base_dir).join()
    assert list(base_dir_as_path.iterdir()) == [f1]


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
