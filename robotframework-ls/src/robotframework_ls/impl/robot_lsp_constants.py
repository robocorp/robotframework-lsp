# Note: there's a copy of these settings at:
# robotframework_interactive.server.rf_interpreter_ls_config
# which should be kept up-to-date with this one.

from typing import List
from .robot_generated_lsp_constants import *  # @UnusedWildImport

# Some aliases for backward compatibility.
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM = (
    OPTION_ROBOT_COMPLETIONS_SECTION_HEADERS_FORM
)
OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR = (
    OPTION_ROBOT_COMPLETIONS_KEYWORDS_ARGUMENTS_SEPARATOR
)
OPTION_ROBOT_SHOW_CODE_LENSES = OPTION_ROBOT_CODE_LENS_ENABLE
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT = OPTION_ROBOT_COMPLETIONS_KEYWORDS_FORMAT
OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE = (
    OPTION_ROBOT_LOAD_VARIABLES_FROM_ARGUMENTS_FILE
)
OPTION_ROBOT_VARIABLES_LOAD_FROM_VARIABLES_FILE = (
    OPTION_ROBOT_LOAD_VARIABLES_FROM_VARIABLES_FILE
)


OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY = "robotidy"
OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY = "builtinTidy"

OPTION_ROBOT_FLOW_EXPLORER_THEME_LIGHT = "light"
OPTION_ROBOT_FLOW_EXPLORER_THEME_DARK = "dark"

OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_FIRST_UPPER = "First upper"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_TITLE = "Title Case"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_ALL_LOWER = "all lower"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_ALL_UPPER = "ALL UPPER"

OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL = "plural"
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_SINGULAR = "singular"
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_BOTH = "both"


# Options which must be set as environment variables.
ENV_OPTION_ROBOT_DAP_TIMEOUT = "ROBOT_DAP_TIMEOUT"


CHECK_IF_LIBRARIES_INSTALLED: List[str] = [
    # robotframework-appiumlibrary
    "AppiumLibrary",
    # robotframework-datadriver
    "DataDriver",
    # robotframework-mainframe3270
    "Mainframe3270",
    # robotframework-sshlibrary
    "SSHLibrary",
    # robotframework-whitelibrary
    "WhiteLibrary",
    # rpaframework-google
    "RPA.Cloud.Google",
    # rpaframework
    "RPA.Archive",
    "RPA.Browser",
    "RPA.Browser.Selenium",
    "RPA.Cloud.AWS",
    "RPA.Cloud.Azure",
    "RPA.Crypto",
    "RPA.Database",
    "RPA.Desktop",
    "RPA.Desktop.Clipboard",
    "RPA.Desktop.OperatingSystem",
    "RPA.Desktop.Windows",
    "RPA.Dialogs",
    "RPA.Email.Exchange",
    "RPA.Email.ImapSmtp",
    "RPA.Excel.Application",
    "RPA.Excel.Files",
    "RPA.FileSystem",
    "RPA.FTP",
    "RPA.HTTP",
    "RPA.Images",
    "RPA.JavaAccessBridge",
    "RPA.JSON",
    "RPA.Netsuite",
    "RPA.Notifier",
    "RPA.Outlook.Application",
    "RPA.PDF",
    "RPA.Robocloud.Items",
    "RPA.Robocloud.Secrets",
    "RPA.Robocorp.Process",
    "RPA.Robocorp.Vault",
    "RPA.Robocorp.WorkItems",
    "RPA.RobotLogListener",
    "RPA.Salesforce",
    "RPA.SAP",
    "RPA.Slack",
    "RPA.Tables",
    "RPA.Tasks",
    "RPA.Twitter",
    "RPA.Word.Application",
]
