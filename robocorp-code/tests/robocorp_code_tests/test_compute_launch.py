from robocorp_ls_core import uris


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


def test_compute_launch_action_package_01(tmpdir):
    import os

    from robocorp_code import compute_launch

    package_yaml = tmpdir.join("package.yaml")
    my_action_file = tmpdir.join("my_action.py")
    input_json = tmpdir.join("input.json")

    my_action_file.write(
        """
from robocorp.actions import action

@action
def my_action(arg1: str) -> str:
    return arg1
"""
    )

    package_yaml.write(
        """
# Required: A description of what's in the action package.
description: Action package description

# Required: The current version of this action package.
version: 0.0.1

# Required: A link to where the documentation on the package lives.
documentation: https://github.com/...

dependencies:
  conda-forge:
  - python=3.10.12
  - pip=23.2.1
  - robocorp-truststore=0.8.0
  pypi:
  - robocorp-actions=0.0.7
"""
    )

    input_json.write(
        """
{"arg1": "value"}
"""
    )

    additional_pythonpath_entries = []
    launch = compute_launch.compute_robot_launch_from_robocorp_code_launch(
        "Launch name",
        "launch",
        None,
        None,
        additional_pythonpath_entries,
        None,
        "python_executable.exe",
        package=str(package_yaml),
        action_name="my_action",
        uri=uris.from_fs_path(str(tmpdir.join("my_action.py"))),
        json_input=str(input_json),
    )

    cwd = str(tmpdir)
    expected = {
        "success": True,
        "message": None,
        "result": {
            "type": "python",
            "name": "Launch name",
            "request": "launch",
            "cwd": cwd,
            "module": "robocorp.actions",
            "args": [
                "run",
                "--action",
                "my_action",
                "--json-input",
                os.path.join(cwd, "input.json"),
                # May change drive case:
                uris.to_fs_path(uris.from_fs_path(os.path.join(cwd, "my_action.py"))),
            ],
            "console": "integratedTerminal",
            "internalConsoleOptions": "neverOpen",
            "python": "python_executable.exe",
        },
    }
    assert launch == expected
