import os
from typing import Optional, List, Dict

from robocorp_code.protocols import ActionResultDictRobotLaunch
from robocorp_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


def compute_robot_launch_from_robocorp_code_launch(
    name: Optional[str],
    request: Optional[str],
    task: Optional[str],
    robot: Optional[str],
    additional_pythonpath_entries: Optional[List[str]],
    env: Optional[Dict[str, str]],
    python_exe: Optional[str],
) -> ActionResultDictRobotLaunch:

    if not name:
        return {
            "success": False,
            "message": "'name' must be specified to make launch.",
            "result": None,
        }
    if not request:
        return {
            "success": False,
            "message": "'request' must be specified to make launch.",
            "result": None,
        }
    if not robot:
        return {
            "success": False,
            "message": "'robot' must be specified to make launch.",
            "result": None,
        }

    if not os.path.isfile(robot):
        return {
            "success": False,
            "message": f"The specified robot.yaml does not exist or is not a file ({robot}).",
            "result": None,
        }

    try:

        from robocorp_ls_core import yaml_wrapper

        with open(robot, "r") as stream:
            yaml_contents = yaml_wrapper.load(stream)

        if not yaml_contents:
            raise RuntimeError("Empty yaml contents.")
        if not isinstance(yaml_contents, dict):
            raise RuntimeError("Expected yaml contents root to be a dict.")
    except:
        log.exception("Error loading contents from: %s", robot)
        return {
            "success": False,
            "message": f"Unable to load robot.yaml contents from: ({robot}).",
            "result": None,
        }

    tasks = yaml_contents.get("tasks")
    if not tasks:
        return {
            "success": False,
            "message": "Expected the robot.yaml to have the 'tasks' defined.",
            "result": None,
        }

    if not isinstance(tasks, dict):
        return {
            "success": False,
            "message": f"Expected the robot.yaml 'tasks' to be a dict of tasks. Found: {type(tasks)}.",
            "result": None,
        }

    if not task:
        if len(tasks) == 1:
            task = next(iter(tasks))
        else:
            return {
                "success": False,
                "message": f"'task' must be specified in launch when Robot contains more than 1 task. Available tasks: {', '.join(list(tasks))}.",
                "result": None,
            }

    task_info = tasks.get(task)
    if not task_info:
        return {
            "success": False,
            "message": f"Unable to find task: {task} in the Robot: {robot}.",
            "result": None,
        }
    if not isinstance(task_info, dict):
        return {
            "success": False,
            "message": f"Expected the task: {task} to be a dict. Found: {type(task_info)}.",
            "result": None,
        }

    command = task_info.get("command")
    if not command:
        shell = task_info.get("shell")
        if shell:
            import shlex

            command = shlex.split(shell, posix=True)
        else:
            robot_task_name = task_info.get("robotTaskName")
            if robot_task_name:
                command = [
                    "python",
                    "-m",
                    "robot",
                    "--report",
                    "NONE",
                    "--outputdir",
                    "output",
                    "--logtitle",
                    "Task log",
                    "--task",
                    robot_task_name,
                    os.path.dirname(robot),
                ]
            else:
                return {
                    "success": False,
                    "message": f"Expected the task: {task} to have the command/shell/robotTaskName defined.",
                    "result": None,
                }

    if not isinstance(command, list):
        return {
            "success": False,
            "message": f"Expected the task: {task} to have a list(str) as the command. Found: {type(command)}.",
            "result": None,
        }

    command = [str(c) for c in command]
    cwd = os.path.dirname(robot)

    if command[:3] == ["python", "-m", "robot"]:
        args: List[str] = command[3:]

        if not args:
            return {
                "success": False,
                "message": (
                    f"Expected the robot file/directory to be executed to be provided"
                ),
                "result": None,
            }

        target_last = args[-1]
        if not os.path.isabs(target_last):
            target_last = os.path.abspath(
                os.path.join(os.path.dirname(robot), target_last)
            )

        if os.path.exists(target_last):
            target = target_last
            args = args[:-1]  # i.e.: Remove python -m robot ... target
        else:
            # Not the last...also check if the first argument is the target.
            target_first = args[0]

            if not os.path.isabs(target_first):
                target_first = os.path.abspath(
                    os.path.join(os.path.dirname(robot), target_first)
                )

            if os.path.exists(target_first):
                target = target_first
                args = args[1:]  # i.e.: Remove python -m robot ... target ...

            else:
                return {
                    "success": False,
                    "message": (
                        f"Expected the first/last argument to be the robot file/directory to be executed. Found: first:{target_first}, last:{target_last}"
                    ),
                    "result": None,
                }

        if additional_pythonpath_entries:
            for s in additional_pythonpath_entries:
                args.append("--pythonpath")
                args.append(s)

        result = {
            "type": "robotframework-lsp",
            "name": name,
            "request": request,
            "target": target,
            "cwd": cwd,
            "args": args,
            "terminal": "none",
        }
        if env:
            result["env"] = env
        return {"success": True, "message": None, "result": result}

    elif command[:1] == ["python"]:
        # It must be something as:
        # python [option] ... [-c cmd | -m mod | file | -] [arg]
        module = None
        program = None
        vmargs = []
        for i, c in enumerate(command):
            if i == 0:
                continue  # skip 'python'
            if c == "-m":
                module = command[i + 1]
                vmargs = command[1:i]
                args = command[i + 2 :]
                break

            elif c == "-c":
                return {
                    "success": False,
                    "message": f"Unable to deal with running with python '-c' flag.",
                    "result": None,
                }

            else:
                if not os.path.isabs(c):
                    c = os.path.abspath(os.path.join(os.path.dirname(robot), c))

                if os.path.exists(c):
                    program = c
                    vmargs = command[1:i]
                    args = command[i + 1 :]
                    break

        else:
            return {
                "success": False,
                "message": f"Unable to detect module or program to be launched.",
                "result": None,
            }

        result = {
            "type": "python",
            "name": name,
            "request": request,
            "cwd": cwd,
            "args": args,
            "pythonArgs": vmargs,
            "console": "internalConsole",
        }

        if python_exe:
            result["pythonPath"] = python_exe

        if module is not None:
            result["module"] = module
        elif program is not None:
            result["program"] = program
        else:
            return {
                "success": False,
                "message": f"Unable to detect module or program to be launched (unexpected error).",
                "result": None,
            }

        if env:
            result["env"] = env

        return {"success": True, "message": None, "result": result}

    else:
        return {
            "success": False,
            "message": (
                f"Currently it's only possible to debug Robot Framework or python tasks "
                f"(i.e.: the task must start with 'python -m robot' or 'python'). Task command: {command}"
            ),
            "result": None,
        }
