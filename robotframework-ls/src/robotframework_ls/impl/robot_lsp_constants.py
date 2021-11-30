from typing import List

OPTION_ROBOT_PYTHON_EXECUTABLE = "robot.python.executable"

OPTION_ROBOT_PYTHON_ENV = "robot.python.env"

OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT = "robot.language-server.tcp-port"

OPTION_ROBOT_LANGUAGE_SERVER_ARGS = "robot.language-server.args"

OPTION_ROBOT_VARIABLES = "robot.variables"

OPTION_ROBOT_LINT_ROBOCOP_ENABLED = "robot.lint.robocop.enabled"

OPTION_ROBOT_CODE_FORMATTER = "robot.codeFormatter"

OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY = "robotidy"
OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY = "builtinTidy"

OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT = "robot.completions.keywords.format"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_FIRST_UPPER = "First upper"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_TITLE = "Title Case"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_ALL_LOWER = "all lower"
OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT_ALL_UPPER = "ALL UPPER"


OPTION_ROBOT_PYTHONPATH = "robot.pythonpath"
OPTION_ROBOT_LIBRARIES_LIBDOC_NEEDS_ARGS = "robot.libraries.libdoc.needsArgs"
OPTION_ROBOT_LIBRARIES_LIBDOC_PRE_GENERATE = "robot.libraries.libdoc.preGenerate"

OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS = (
    "robot.workspaceSymbolsOnlyForOpenDocs"
)

OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM = "robot.completions.section_headers.form"
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL = "plural"
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_SINGULAR = "singular"
OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_BOTH = "both"

# Options which must be set as environment variables.
ENV_OPTION_ROBOT_DAP_TIMEOUT = "ROBOT_DAP_TIMEOUT"


ALL_ROBOT_OPTIONS = frozenset(
    (
        OPTION_ROBOT_PYTHON_EXECUTABLE,
        OPTION_ROBOT_PYTHON_ENV,
        OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT,
        OPTION_ROBOT_LANGUAGE_SERVER_ARGS,
        OPTION_ROBOT_VARIABLES,
        OPTION_ROBOT_LINT_ROBOCOP_ENABLED,
        OPTION_ROBOT_PYTHONPATH,
        OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM,
        OPTION_ROBOT_WORKSPACE_SYMBOLS_ONLY_FOR_OPEN_DOCS,
        OPTION_ROBOT_COMPLETION_KEYWORDS_FORMAT,
        OPTION_ROBOT_LIBRARIES_LIBDOC_NEEDS_ARGS,
    )
)


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
