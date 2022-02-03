from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def get_robot_version():
    try:
        import robot  # noqa

        v = str(robot.get_version())
    except:
        log.exception("Unable to get robot version.")
        v = "unknown"
    return v


def get_robot_major_version():
    robot_version = get_robot_version()

    major_version = 4
    try:
        if "." in robot_version:
            major_version = int(robot_version.split(".")[0])
    except:
        log.exception("Unable to get robot major version.")

    return major_version
