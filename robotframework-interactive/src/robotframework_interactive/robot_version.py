def _get_robot_naked_version():
    import robot  # noqa

    return str(robot.get_version(True))


def get_robot_major_version() -> int:
    robot_version = _get_robot_naked_version()

    major_version = int(robot_version.split(".")[0])
    return major_version
