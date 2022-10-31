def _get_robot_naked_version():
    import robot  # noqa

    return str(robot.get_version(True))


_found_major_version = None


def get_robot_major_version() -> int:
    global _found_major_version
    if _found_major_version is not None:
        return _found_major_version

    robot_version = _get_robot_naked_version()
    major_version = int(robot_version.split(".")[0])
    _found_major_version = major_version
    return major_version
