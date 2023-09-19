from pathlib import Path
from typing import Optional


def find_robot_yaml_path_from_path(path: Path, stat) -> Optional[Path]:
    """
    To be used as:

    path = Path(robot)
    try:
        stat = path.stat()
    except Exception:
        message = f"Expected {path} to exist."
        log.exception(message)
        return dict(success=False, message=message, result=None)

    robot_yaml = find_robot_yaml_path_from_path(path, stat)
    """
    from stat import S_ISDIR

    if not S_ISDIR(stat.st_mode):
        # If we have the stat it already exists, so, just checking if it's a dir/file.
        if path.name == "robot.yaml":
            return path
        else:
            path = path.parent

    for _i in range(10):
        robot_yaml = path / "robot.yaml"
        if robot_yaml.is_file():
            return robot_yaml
        parent = path.parent
        if not parent:
            return None
        if parent == path:
            return None
        path = parent

    return robot_yaml
