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
            "console": "internalConsole",
            "program": os.path.join(cwd, "task.py"),
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
            "console": "internalConsole",
            "program": os.path.join(cwd, "task.py"),
            "pythonPath": "python_executable.exe",
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
            "console": "internalConsole",
            "module": "module_name",
            "pythonPath": "python_executable.exe",
        },
    }
