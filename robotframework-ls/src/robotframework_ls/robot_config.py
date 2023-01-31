from robocorp_ls_core.config import Config
from robotframework_ls.impl.robot_lsp_constants import ALL_ROBOT_OPTIONS
import os.path
from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.protocols import IConfig
from robocorp_ls_core.robotframework_log import get_logger
from typing import Optional, Dict

log = get_logger(__name__)


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


def get_arguments_separator(completion_context: ICompletionContext):
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


def get_robot_libraries_deprecated_name_to_replacement(
    config: Optional[IConfig],
) -> Dict[str, str]:
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LIBRARIES_DEPRECATED,
    )

    deprecated_library_name_to_replacement: Dict[str, str] = {}
    if not config:
        return deprecated_library_name_to_replacement

    deprecated = config.get_setting(OPTION_ROBOT_LIBRARIES_DEPRECATED, list, [])
    if deprecated:
        bad_input = None
        for entry in deprecated:
            if isinstance(entry, str):
                deprecated_library_name_to_replacement[entry] = "*DEPRECATED* "
            elif isinstance(entry, dict):
                name = str(entry.get("name", ""))
                if not name:
                    bad_input = f"Entry with no name: {entry}."
                    continue
                replacement = str(entry.get("replacement", ""))
                if replacement:
                    deprecated_library_name_to_replacement[
                        name
                    ] = f"*DEPRECATED* Please use {replacement} instead. "
                else:
                    deprecated_library_name_to_replacement[name] = f"*DEPRECATED* "
            else:
                bad_input = f"Unexpected entry type: {entry} ({type(entry)})."

        if bad_input:
            log.critical(
                f"Wrong format for: {OPTION_ROBOT_LIBRARIES_DEPRECATED}: {bad_input}"
            )

    return deprecated_library_name_to_replacement
