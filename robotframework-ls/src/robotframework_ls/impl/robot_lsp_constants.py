from typing import List

OPTION_ROBOT_PYTHON_EXECUTABLE = "robot.python.executable"

OPTION_ROBOT_PYTHON_ENV = "robot.python.env"

OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT = "robot.language-server.tcp-port"

OPTION_ROBOT_LANGUAGE_SERVER_ARGS = "robot.language-server.args"

OPTION_ROBOT_VARIABLES = "robot.variables"
OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE = "robot.loadVariablesFromArgumentsFile"

OPTION_ROBOT_LINT_ROBOCOP_ENABLED = "robot.lint.robocop.enabled"

OPTION_ROBOT_LINT_ENABLED = "robot.lint.enabled"
OPTION_ROBOT_LINT_UNDEFINED_KEYWORDS = "robot.lint.undefinedKeywords"
OPTION_ROBOT_LINT_UNDEFINED_LIBRARIES = "robot.lint.undefinedLibraries"
OPTION_ROBOT_LINT_UNDEFINED_RESOURCES = "robot.lint.undefinedResources"
OPTION_ROBOT_LINT_UNDEFINED_VARIABLE_IMPORTS = "robot.lint.undefinedVariableImports"
OPTION_ROBOT_LINT_KEYWORD_CALL_ARGUMENTS = "robot.lint.keywordCallArguments"

OPTION_ROBOT_LINT_VARIABLES = "robot.lint.variables"
OPTION_ROBOT_LINT_IGNORE_VARIABLES = "robot.lint.ignoreVariables"
OPTION_ROBOT_LINT_IGNORE_ENVIRONMENT_VARIABLES = "robot.lint.ignoreEnvironmentVariables"


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

OPTION_ROBOT_SHOW_CODE_LENSES = "robot.codeLens.enable"

OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR = (
    "robot.completions.keywords.argumentsSeparator"
)

# Options which must be set as environment variables.
ENV_OPTION_ROBOT_DAP_TIMEOUT = "ROBOT_DAP_TIMEOUT"


# Load all robot options.
_robot_options = []
for _k, _v in dict(globals()).items():
    if isinstance(_k, str) and isinstance(_v, str):
        if _k.startswith("OPTION") and _v.startswith("robot."):
            _robot_options.append(_v)

del _k
del _v

ALL_ROBOT_OPTIONS = frozenset(_robot_options)
del _robot_options


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
