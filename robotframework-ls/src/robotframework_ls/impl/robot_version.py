from robocorp_ls_core.robotframework_log import get_logger
from typing import Tuple

log = get_logger(__name__)


def get_robot_version() -> str:
    try:
        import robot  # noqa

        v = str(robot.get_version())
    except:
        log.exception("Unable to get robot version.")
        v = "unknown"
    return v


def _get_robot_naked_version():
    try:
        import robot  # noqa

        v = str(robot.get_version(True))
    except:
        log.exception("Unable to get robot version.")
        v = "unknown"
    return v


_found_major_version = None


def get_robot_major_version() -> int:
    global _found_major_version
    if _found_major_version is not None:
        return _found_major_version

    robot_version = _get_robot_naked_version()

    major_version = 4
    try:
        if "." in robot_version:
            major_version = int(robot_version.split(".")[0])
            _found_major_version = major_version
    except:
        log.exception("Unable to get robot major version.")

    return major_version


_found_major_minor_version = None


def get_robot_major_minor_version() -> Tuple[int, int]:
    global _found_major_minor_version
    if _found_major_minor_version is not None:
        return _found_major_minor_version

    robot_version = _get_robot_naked_version()

    major_minor_version = (4, 0)
    try:
        if "." in robot_version:
            split = robot_version.split(".")
            major_version = int(split[0])
            minor_version = int(split[1])
            major_minor_version = _found_major_minor_version = (
                major_version,
                minor_version,
            )
    except:
        log.exception("Unable to get robot major/minor version.")

    return major_minor_version


def robot_version_supports_language():
    return get_robot_major_minor_version() >= (5, 1)
