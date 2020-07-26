"""
Constants that help in describing the accepted structure of a file.
"""
from typing import Tuple, Dict

BDD_PREFIXES = ["given ", "when ", "then ", "and ", "but "]
VARIABLE_PREFIXES = ("@", "%", "$", "&")


# From: robot.variables.scopes.GlobalVariables._set_built_in_variables
# (var name and description)
BUILTIN_VARIABLES = [
    ("${TEMPDIR}", "abspath(tempfile.gettempdir())"),
    ("${EXECDIR}", "abspath('.')"),
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
        "Reserved",
        "Screenshot",
        "String",
        "Telnet",
        "XML",
    )
)
