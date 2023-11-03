def test_compute_launch_robot(tmpdir):
    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        f"""
tasks:
  Default:
    command:
      - python
      - -m
      - robot
      - {str(tmpdir)}

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        None,
    )

    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "robotframework-lsp",
            "name": "Launch name",
            "request": "launch",
            "target": "<target-in-args>",
            "cwd": str(tmpdir),
            "args": [str(tmpdir)],
            "terminal": "integrated",
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_robot_shell(tmpdir):
    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    d = str(tmpdir).replace("\\", "/")
    robot_yaml.write(
        f"""
tasks:
  Default:
    shell: python -m robot {d} "task name"

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        None,
    )

    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "robotframework-lsp",
            "name": "Launch name",
            "request": "launch",
            "target": "<target-in-args>",
            "cwd": str(tmpdir),
            "args": [d, "task name"],
            "terminal": "integrated",
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_robot_taskname(tmpdir):
    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        f"""
tasks:
  Default:
    robotTaskName: my Task

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        None,
    )

    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "robotframework-lsp",
            "name": "Launch name",
            "request": "launch",
            "target": "<target-in-args>",
            "cwd": str(tmpdir),
            "args": [
                "--report",
                "NONE",
                "--outputdir",
                "output",
                "--logtitle",
                "Task log",
                "--task",
                "my Task",
                str(tmpdir),
            ],
            "terminal": "integrated",
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_01(tmpdir):
    import os

    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        """
tasks:
  Default:
    command:
      - python
      - task.py

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        None,
    )

    cwd = str(tmpdir)
    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "python",
            "name": "Launch name",
            "request": "launch",
            "cwd": cwd,
            "args": [],
            "pythonArgs": [],
            "console": "integratedTerminal",
            "program": os.path.join(cwd, "task.py"),
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_02(tmpdir):
    import os

    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        """
tasks:
  Default:
    command:
      - python
      - task.py
      - arg1

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        "python_executable.exe",
    )

    cwd = str(tmpdir)
    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "python",
            "name": "Launch name",
            "request": "launch",
            "cwd": cwd,
            "args": ["arg1"],
            "pythonArgs": [],
            "console": "integratedTerminal",
            "program": os.path.join(cwd, "task.py"),
            "python": "python_executable.exe",
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_03(tmpdir):
    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    robot_yaml.write(
        """
tasks:
  Default:
    command:
      - python
      - -c
      - print('something')
      - arg1

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        None,
    )

    assert not launch["success"]
    assert launch["message"] == "Unable to deal with running with python '-c' flag."


def test_compute_launch_04(tmpdir):
    import os

    from robocorp_code import compute_launch

    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        """
tasks:
  Default:
    command:
      - python
      - -u
      - -m
      - module_name
      - arg1

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "Default",
        str(robot_yaml),
        additional_pythonpath_entries,
        None,
        "python_executable.exe",
    )

    cwd = str(tmpdir)
    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "python",
            "name": "Launch name",
            "request": "launch",
            "cwd": cwd,
            "args": ["arg1"],
            "pythonArgs": ["-u"],
            "console": "integratedTerminal",
            "module": "module_name",
            "python": "python_executable.exe",
            "internalConsoleOptions": "neverOpen",
        },
    }


def test_compute_launch_05(tmpdir):
    from robocorp_code import compute_launch

    env = {"some_key": "some_value"}
    robot_yaml = tmpdir.join("robot.yaml")
    tmpdir.join("task.py").write("foo")
    robot_yaml.write(
        """
tasks:
  Default:
    command:
      - python
      - -u
      - -m
      - module_name
      - arg1

condaConfigFile: conda.yaml
artifactsDir: output
PATH:
  - .
PYTHONPATH:
  - .
ignoreFiles:
    - .gitignore
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        "",  # Don't provide task name: should be ok if only 1 task is there.
        str(robot_yaml),
        additional_pythonpath_entries,
        env,
        "python_executable.exe",
    )

    cwd = str(tmpdir)
    assert launch == {
        "success": True,
        "message": None,
        "result": {
            "type": "python",
            "name": "Launch name",
            "request": "launch",
            "cwd": cwd,
            "args": ["arg1"],
            "pythonArgs": ["-u"],
            "console": "integratedTerminal",
            "module": "module_name",
            "python": "python_executable.exe",
            "env": {"some_key": "some_value"},
            "internalConsoleOptions": "neverOpen",
        },
    }
