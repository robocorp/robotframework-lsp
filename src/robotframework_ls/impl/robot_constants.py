"""
Constants that help in describing the accepted structure of a file.
"""

BDD_PREFIXES = ["given ", "when ", "then ", "and ", "but "]


class Section(object):

    # Header to the section (i.e.: *** Setting ***)
    markers = ()

    # Names that can appear under the section.
    names = ()

    # Aliases for names (so, it's possible to use either an alias or the
    # name itself).
    aliases = {}

    # The names that can appear multiple times.
    multi_use = ("Metadata", "Library", "Resource", "Variables")

    names_in_brackets = True


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
