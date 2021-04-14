"""
Constants that help in describing the accepted structure of a file.
"""
from typing import Tuple, Dict
import os

BDD_PREFIXES = ["given ", "when ", "then ", "and ", "but "]
VARIABLE_PREFIXES = ("@", "%", "$", "&")


# From: robot.variables.scopes.GlobalVariables._set_built_in_variables
# (var name and description)
BUILTIN_VARIABLES = [
    ("${TEMPDIR}", "abspath(tempfile.gettempdir())"),
    ("${EXECDIR}", "abspath('.')"),
    ("${CURDIR}", "abspath('.')"),
    ("${/}", "os.sep"),
    ("${:}", "os.pathsep"),
    ("${\\n}", "os.linesep"),
    ("${SPACE}", " "),
    ("${True}", "True"),
    ("${False}", "False"),
    ("${None}", "None"),
    ("${null}", "None"),
    ("${OUTPUT_DIR}", "settings.output_directory"),
    ("${OUTPUT_FILE}", "settings.output or 'NONE'"),
    ("${REPORT_FILE}", "settings.report or 'NONE'"),
    ("${LOG_FILE}", "settings.log or 'NONE'"),
    ("${DEBUG_FILE}", "settings.debug_file or 'NONE'"),
    ("${LOG_LEVEL}", "settings.log_level"),
    ("${PREV_TEST_NAME}", ""),
    ("${PREV_TEST_STATUS}", ""),
    ("${PREV_TEST_MESSAGE}", ""),
    # Also available during runtime (but not in docs?!).
    ("${SUITE_DOCUMENTATION}", ""),
    ("${SUITE_NAME}", ""),
    ("${SUITE_SOURCE}", ""),
    ("${TEST_DOCUMENTATION}", ""),
    ("${TEST_NAME}", ""),
    ("&{SUITE_METADATA}", ""),
    ("@{TEST_TAGS}", ""),
]

# i.e.: Just the variables we can resolve statically...
BUILTIN_VARIABLES_RESOLVED = dict(
    [("/", os.sep), (":", os.pathsep), ("\\n", os.linesep), ("SPACE", " ")]
)


class Section(object):

    # Header to the section (i.e.: *** Setting ***)
    markers: Tuple[str, ...] = ()

    # Names that can appear under the section.
    names: Tuple[str, ...] = ()

    # Aliases for names (so, it's possible to use either an alias or the
    # name itself).
    aliases: Dict[str, str] = {}

    # The names that can appear multiple times.
    multi_use: Tuple[str, ...] = ("Metadata", "Library", "Resource", "Variables")

    names_in_brackets: bool = True


class TestCaseFileSettingsSection(Section):
    markers = ("Setting", "Settings")
    names_in_brackets = False

    names = (
        "Documentation",
        "Metadata",
        "Suite Setup",
        "Suite Teardown",
        "Test Setup",
        "Test Teardown",
        "Test Template",
        "Test Timeout",
        "Force Tags",
        "Default Tags",
        "Library",
        "Resource",
        "Variables",
    )
    aliases = {
        "Task Setup": "Test Setup",
        "Task Teardown": "Test Teardown",
        "Task Template": "Test Template",
        "Task Timeout": "Test Timeout",
    }


class InitFileSettingsSection(Section):
    markers = ("Setting", "Settings")
    names_in_brackets = False

    names = (
        "Documentation",
        "Metadata",
        "Suite Setup",
        "Suite Teardown",
        "Test Setup",
        "Test Teardown",
        "Test Timeout",
        "Force Tags",
        "Library",
        "Resource",
        "Variables",
    )


class ResourceFileSettingsSection(Section):
    markers = ("Setting", "Settings")
    names_in_brackets = False

    names = ("Documentation", "Library", "Resource", "Variables")


class VariableSection(Section):
    markers = ("Variables", "Variable")


class TestCaseSection(Section):
    markers = ("Test Cases", "Test Case", "Tasks", "Task")

    names = ("Documentation", "Tags", "Setup", "Teardown", "Template", "Timeout")


class KeywordSection(Section):
    markers = ("Keywords", "Keyword")

    names = ("Documentation", "Arguments", "Teardown", "Timeout", "Tags", "Return")


class CommentSection(Section):
    markers = ("Comment", "Comments")


# Sections that can appear in a test case
TEST_CASE_FILE_SECTIONS = [
    TestCaseFileSettingsSection,
    VariableSection,
    TestCaseSection,
    KeywordSection,
    CommentSection,
]

# Sections that can appear in an init file
INIT_FILE_SECTIONS = [
    InitFileSettingsSection,
    VariableSection,
    KeywordSection,
    CommentSection,
]

# Sections that can appear in a resource file
RESOURCE_FILE_SECTIONS = [
    ResourceFileSettingsSection,
    VariableSection,
    KeywordSection,
    CommentSection,
]


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


## Token types gotten from: robot.parsing.lexer.tokens.Token


SETTING_HEADER = "SETTING HEADER"
VARIABLE_HEADER = "VARIABLE HEADER"
TESTCASE_HEADER = "TESTCASE HEADER"
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
ELSE_IF = "ELSE IF"
ELSE = "ELSE"

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
    (SETTING_HEADER, VARIABLE_HEADER, TESTCASE_HEADER, KEYWORD_HEADER, COMMENT_HEADER)
)
ALLOW_VARIABLES = frozenset((NAME, ARGUMENT, TESTCASE_NAME, KEYWORD_NAME))

CONTROL_TOKENS = frozenset(
    (FOR, IF, ELSE, ELSE_IF, END, WITH_NAME, FOR_SEPARATOR, ASSIGN)
)
