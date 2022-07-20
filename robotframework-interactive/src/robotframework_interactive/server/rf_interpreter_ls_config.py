# NOTE: This is a copy of the settings from the language server so that we don't
# have a cyclic dependency.

# So, if this is changed,
# robotframework_ls.impl.robot_lsp_constants
# should also be updated

from robocorp_ls_core.config import Config

OPTION_ROBOT_PYTHON_EXECUTABLE = "robot.python.executable"

OPTION_ROBOT_PYTHON_ENV = "robot.python.env"

OPTION_ROBOT_LANGUAGE_SERVER_TCP_PORT = "robot.language-server.tcp-port"

OPTION_ROBOT_LANGUAGE_SERVER_ARGS = "robot.language-server.args"

OPTION_ROBOT_VARIABLES = "robot.variables"
OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE = "robot.loadVariablesFromArgumentsFile"

OPTION_ROBOT_INTERACTIVE_CONSOLE_ARGUMENTS = "robot.interactiveConsole.arguments"

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

# NOTE: This is a copy of the settings from the language server so that we don't
# have a cyclic dependency.


class RfInterpreterRobotConfig(Config):
    ALL_OPTIONS = ALL_ROBOT_OPTIONS
