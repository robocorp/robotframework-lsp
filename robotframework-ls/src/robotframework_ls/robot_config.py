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


def create_convert_keyword_format_func(config):
    if config is not None:
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT,
        )

        keyword_format = config.get_setting(
            OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT, str, ""
        )

        if keyword_format:
            keyword_format = keyword_format.lower().replace(" ", "_").strip()
            # Convert its format depending on
            # the user configuration.
            if keyword_format == "first_upper":
                return lambda label: label.capitalize()

            elif keyword_format == "title_case":
                return lambda label: label.title()

            elif keyword_format == "all_lower":
                return lambda label: label.lower()

            elif keyword_format == "all_upper":
                return lambda label: label.upper()

    return lambda x: x


def get_arguments_separator(completion_context):
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_ARGUMENTS_SEPARATOR,
    )

    separator = "    "
    config = completion_context.config
    if config is not None:
        separator = config.get_setting(
            OPTION_ROBOT_COMPLETIONS_KEYWORDS_ARGUMENTS_SEPARATOR, str, "    "
        )
    return separator
