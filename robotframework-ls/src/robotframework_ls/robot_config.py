from robocorp_ls_core.config import Config
from robotframework_ls.impl.robot_lsp_constants import ALL_ROBOT_OPTIONS
import os.path


class RobotConfig(Config):
    ALL_OPTIONS = ALL_ROBOT_OPTIONS


def get_robotframework_ls_home():
    user_home = os.getenv("ROBOTFRAMEWORK_LS_USER_HOME", None)
    if user_home is None:
        user_home = os.path.expanduser("~")

    return os.path.join(user_home, ".robotframework-ls")
