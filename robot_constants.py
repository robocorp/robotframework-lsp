"""
Constants that help in describing the accepted structure of a file.
"""
import os
from functools import lru_cache

BDD_PREFIXES = ["given", "when", "then", "and", "but"]
VARIABLE_PREFIXES = ("@", "%", "$", "&")

ROBOT_FILE_EXTENSIONS = (".robot", ".resource")
ROBOT_AND_TXT_FILE_EXTENSIONS = ROBOT_FILE_EXTENSIONS + (".txt",)
LIBRARY_FILE_EXTENSIONS = (".py",)

# Extensions which may have keywords
ALL_KEYWORD_RELATED_FILE_EXTENSIONS = (
    ROBOT_AND_TXT_FILE_EXTENSIONS + LIBRARY_FILE_EXTENSIONS
)

VARIABLE_FILE_EXTENSIONS = (".yaml", ".yml")

# From: robot.variables.scopes.GlobalVariables._set_built_in_variables
# (var name and description)
_BUILTIN_VARIABLES = (
    ("TEMPDIR", "abspath(tempfile.gettempdir())"),
    ("EXECDIR", "abspath('.')"),
    ("CURDIR", "abspath('.')"),
    ("/", "os.sep"),
    (":", "os.pathsep"),
    ("\\n", "os.linesep"),
    ("SPACE", " "),
    ("True", "True"),
    ("False", "False"),
    ("None", "None"),
    ("null", "None"),
    ("EMPTY", ""),
    ("OUTPUT_DIR", "settings.output_directory"),
    ("OUTPUT_FILE", "settings.output or 'NONE'"),
    ("REPORT_FILE", "settings.report or 'NONE'"),
    ("LOG_FILE", "settings.log or 'NONE'"),
    ("DEBUG_FILE", "settings.debug_file or 'NONE'"),
    ("LOG_LEVEL", "settings.log_level"),
    ("KEYWORD_STATUS", ""),
    ("KEYWORD_MESSAGE", ""),
    ("TEST_STATUS", ""),
    ("TEST_MESSAGE", ""),
    ("PREV_TEST_NAME", ""),
    ("PREV_TEST_STATUS", ""),
    ("PREV_TEST_MESSAGE", ""),
    # Also available during runtime (but not in docs?!).
    ("SUITE_DOCUMENTATION", ""),
    ("SUITE_NAME", ""),
    ("SUITE_SOURCE", ""),
    ("SUITE_STATUS", ""),
    ("SUITE_MESSAGE", ""),
    ("TEST_DOCUMENTATION", ""),
    ("TEST_NAME", ""),
    ("SUITE_METADATA", ""),
    ("TEST_TAGS", ""),
)

_RF5_BUILTIN_VARIABLES = (("OPTIONS", ""),)


@lru_cache(None)
def get_builtin_variables():
    from robotframework_ls.impl.robot_version import get_robot_major_version

    v = get_robot_major_version()
    if v >= 5:
        return _BUILTIN_VARIABLES + _RF5_BUILTIN_VARIABLES
    return _BUILTIN_VARIABLES


# i.e.: Just the variables we can resolve statically...
BUILTIN_VARIABLES_RESOLVED = dict(
    [("/", os.sep), (":", os.pathsep), ("\\n", os.linesep), ("SPACE", " ")]
)


BUILTIN_LIB = "BuiltIn"
RESERVED_LIB = "Reserved"

# From robot.libraries.STDLIBS
STDLIBS = frozenset(
    (
        BUILTIN_LIB,
        "Collections",
        "DateTime",
        "Dialogs",
        "Easter",
        "OperatingSystem",
        "Process",
        # "Remote", -- Remote doesn't really have any keywords.
        RESERVED_LIB,
        "Screenshot",
        "String",
        "Telnet",
        "XML",
    )
)

STDLIBS_LOWER = frozenset(x.lower() for x in STDLIBS)

## Token types gotten from: robot.parsing.lexer.tokens.Token


SETTING_HEADER = "SETTING HEADER"
VARIABLE_HEADER = "VARIABLE HEADER"
TESTCASE_HEADER = "TESTCASE HEADER"
TASK_HEADER = "TASK HEADER"  # Only available in RF 5.1
KEYWORD_HEADER = "KEYWORD HEADER"
COMMENT_HEADER = "COMMENT HEADER"

TESTCASE_NAME = "TESTCASE NAME"
KEYWORD_NAME = "KEYWORD NAME"

DOCUMENTATION = "DOCUMENTATION"
SUITE_SETUP = "SUITE SETUP"
SUITE_TEARDOWN = "SUITE TEARDOWN"
METADATA = "METADATA"
TEST_SETUP = "TEST SETUP"
TEST_TEARDOWN = "TEST TEARDOWN"
TEST_TEMPLATE = "TEST TEMPLATE"
TEST_TIMEOUT = "TEST TIMEOUT"
FORCE_TAGS = "FORCE TAGS"
DEFAULT_TAGS = "DEFAULT TAGS"
LIBRARY = "LIBRARY"
RESOURCE = "RESOURCE"
VARIABLES = "VARIABLES"
SETUP = "SETUP"
TEARDOWN = "TEARDOWN"
TEMPLATE = "TEMPLATE"
TIMEOUT = "TIMEOUT"
TAGS = "TAGS"
ARGUMENTS = "ARGUMENTS"
RETURN = "RETURN"
RETURN_SETTING = RETURN

NAME = "NAME"
VARIABLE = "VARIABLE"
ARGUMENT = "ARGUMENT"
ASSIGN = "ASSIGN"
KEYWORD = "KEYWORD"
WITH_NAME = "WITH NAME"
FOR = "FOR"
FOR_SEPARATOR = "FOR SEPARATOR"
END = "END"
IF = "IF"
INLINE_IF = "INLINE IF"
ELSE_IF = "ELSE IF"
ELSE = "ELSE"
TRY = "TRY"
EXCEPT = "EXCEPT"
FINALLY = "FINALLY"
AS = "AS"
WHILE = "WHILE"
RETURN_STATEMENT = "RETURN STATEMENT"
CONTINUE = "CONTINUE"
BREAK = "BREAK"
OPTION = "OPTION"

SEPARATOR = "SEPARATOR"
COMMENT = "COMMENT"
CONTINUATION = "CONTINUATION"
EOL = "EOL"
EOS = "EOS"

ERROR = "ERROR"
FATAL_ERROR = "FATAL ERROR"

NON_DATA_TOKENS = frozenset((SEPARATOR, COMMENT, CONTINUATION, EOL, EOS))
SETTING_TOKENS = frozenset(
    (
        DOCUMENTATION,
        SUITE_SETUP,
        SUITE_TEARDOWN,
        METADATA,
        TEST_SETUP,
        TEST_TEARDOWN,
        TEST_TEMPLATE,
        TEST_TIMEOUT,
        FORCE_TAGS,
        DEFAULT_TAGS,
        LIBRARY,
        RESOURCE,
        VARIABLES,
        SETUP,
        TEARDOWN,
        TEMPLATE,
        TIMEOUT,
        TAGS,
        ARGUMENTS,
        RETURN,
    )
)
HEADER_TOKENS = frozenset(
    (
        SETTING_HEADER,
        VARIABLE_HEADER,
        TESTCASE_HEADER,
        TASK_HEADER,
        KEYWORD_HEADER,
        COMMENT_HEADER,
    )
)
ALLOW_VARIABLES = frozenset((NAME, ARGUMENT, TESTCASE_NAME, KEYWORD_NAME))
CONTROL_TOKENS = frozenset(
    (
        FOR,
        IF,
        INLINE_IF,
        ELSE,
        ELSE_IF,
        END,
        WITH_NAME,
        FOR_SEPARATOR,
        ASSIGN,
        TRY,
        EXCEPT,
        FINALLY,
        AS,
        WHILE,
        RETURN_STATEMENT,
        CONTINUE,
        BREAK,
    )
)
