def test_cmdline_with_suite_1(tmpdir):
    """
    Simple case where we just run a .robot directly without any filtering or
    suite.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os

    target = str(tmpdir.join("my.robot"))

    cwd = str(tmpdir)
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=True,
        cwd=cwd,
        suite_target=None,
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--debug",
        target,
    ]

    assert env == {}


def test_cmdline_with_suite_2(tmpdir):
    """
    Case where the user specified a suiteTarget.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os
    import json

    target = str(tmpdir.join("my.robot"))

    cwd = str(tmpdir)
    suite_target = os.path.dirname(cwd)
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=True,
        cwd=cwd,
        suite_target=suite_target,
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--debug",
        "--prerunmodifier=robotframework_debug_adapter.prerun_modifiers.FilteringTestsSuiteVisitor",
        suite_target,
    ]

    assert env == {
        "RFLS_PRERUN_FILTER_TESTS": json.dumps(
            {
                "include": [
                    [
                        target,
                        "*",
                    ]
                ],
                "exclude": [],
            }
        )
    }


def test_cmdline_with_suite_3(tmpdir):
    """
    Case where the user specified multiple entries in the suiteTarget.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os
    import json

    target = str(tmpdir.join("my.robot"))

    cwd = str(tmpdir)
    suite_target = os.path.dirname(cwd)
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=True,
        cwd=cwd,
        suite_target=[suite_target, cwd],
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--debug",
        "--prerunmodifier=robotframework_debug_adapter.prerun_modifiers.FilteringTestsSuiteVisitor",
        suite_target,
        cwd,
    ]

    assert env == {
        "RFLS_PRERUN_FILTER_TESTS": json.dumps(
            {
                "include": [
                    [
                        target,
                        "*",
                    ]
                ],
                "exclude": [],
            }
        )
    }


def test_cmdline_with_suite_4(tmpdir):
    """
    Case where we find a common __init__.robot.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os

    dira = tmpdir.join("a")
    dira.mkdir()

    dirb = tmpdir.join("b")
    dirb.mkdir()

    dira.join("__init__.robot").write_text("", encoding="utf-8")
    dirb.join("__init__.robot").write_text("", encoding="utf-8")
    tmpdir.join("__init__.robot").write_text("", encoding="utf-8")

    f1 = dira.join("f1.robot")
    f1.write_text("", encoding="utf-8")

    f2 = dirb.join("f2.robot")
    f2.write_text("", encoding="utf-8")

    cwd = str(tmpdir)

    target = [str(f1), str(f2)]
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=False,
        cwd=cwd,
        suite_target=None,
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--no-debug",
        "--suite",
        f"{os.path.basename(str(tmpdir))}.a.f1",
        "--suite",
        f"{os.path.basename(str(tmpdir))}.b.f2",
        str(tmpdir),
    ]

    assert env == {}


def test_cmdline_with_suite_5(tmpdir):
    """
    Case where we find 2 different __init__.robot which are not at the root.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os
    import json

    dira = tmpdir.join("a")
    dira.mkdir()

    dirb = tmpdir.join("b")
    dirb.mkdir()

    dira.join("__init__.robot").write_text("", encoding="utf-8")
    dirb.join("__init__.robot").write_text("", encoding="utf-8")

    f1 = dira.join("f1.robot")
    f1.write_text("", encoding="utf-8")

    f2 = dirb.join("f2.robot")
    f2.write_text("", encoding="utf-8")

    cwd = str(tmpdir)

    target = [str(f1), str(f2)]
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=False,
        cwd=cwd,
        suite_target=None,
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--no-debug",
        "--prerunmodifier=robotframework_debug_adapter.prerun_modifiers.FilteringTestsSuiteVisitor",
        str(dira),
        str(dirb),
    ]

    assert env == {
        "RFLS_PRERUN_FILTER_TESTS": json.dumps(
            {
                "include": [
                    [str(f1), "*"],
                    [str(f2), "*"],
                ],
                "exclude": [],
            }
        )
    }


def test_cmdline_with_suite_6(tmpdir):
    """
    Case where we have an __init__.robot in the root.
    """
    from robotframework_debug_adapter.launch_process import compute_cmd_line_and_env
    import sys
    import os

    tmpdir.join("__init__.robot").write_text("", encoding="utf-8")

    f1 = tmpdir.join("f1.robot")
    f1.write_text("", encoding="utf-8")

    cwd = str(tmpdir)

    target = str(tmpdir)
    env = {}

    cmdline, env = compute_cmd_line_and_env(
        "run_py",
        target,
        make_suite=True,
        port=0,
        args=[],
        run_in_debug_mode=False,
        cwd=cwd,
        suite_target=None,
        env=env,
    )
    cmdline[2] = os.path.basename(cmdline[2])
    assert cmdline == [
        sys.executable,
        "-u",
        "run_py",
        "--port",
        "0",
        "--no-debug",
        "--suite",
        f"{os.path.basename(str(tmpdir))}",
        str(tmpdir),
    ]

    assert env == {}
