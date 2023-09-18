from typing import Tuple, List, Optional, Callable, Any

from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ILocalizationInfo,
    ICompletionContext,
    INode,
)
from robotframework_ls.impl.robot_version import (
    get_robot_major_minor_version,
)


log = get_logger(__name__)


class Section(object):
    # Header to the section (i.e.: *** Setting ***)
    markers: Tuple[str, ...] = ()

    # Names that can appear under the section.
    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        raise NotImplementedError()

    # The names that can appear multiple times.
    multi_use: Tuple[str, ...] = ("Metadata", "Library", "Resource", "Variables")

    names_in_brackets: bool = True

    @classmethod
    def markers_for_lang(cls, lang):
        raise NotImplementedError()

    @classmethod
    def names_for_lang(cls, lang):
        raise NotImplementedError()


class _TestCaseFileSettingsSection(Section):
    matches_rf_node_class = "SettingSection"

    markers = ("Setting", "Settings")
    names_in_brackets = False

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return (
            "Documentation",
            "Metadata",
            "Suite Setup",
            "Suite Teardown",
            "Test Setup",
            "Test Teardown",
            "Test Template",
            "Test Timeout",
            "Library",
            "Resource",
            "Variables",
            "Force Tags",
            "Default Tags",
            # Task (aliases for Test).
            "Task Setup",
            "Task Teardown",
            "Task Template",
            "Task Timeout",
        )

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.settings_header,)

    @classmethod
    def names_for_lang(cls, lang):
        # Only called in RF 5.1 onwards (so, we don't need to show deprecated names).
        return (
            lang.documentation_setting,
            lang.metadata_setting,
            lang.suite_setup_setting,
            lang.suite_teardown_setting,
            lang.test_setup_setting,
            lang.task_setup_setting,
            lang.test_teardown_setting,
            lang.task_teardown_setting,
            lang.test_template_setting,
            lang.task_template_setting,
            lang.test_timeout_setting,
            lang.task_timeout_setting,
            lang.test_tags_setting,  # In place of Force Tags
            lang.task_tags_setting,  # In place of Force Tags
            # "Force Tags",  # Deprecated: https://github.com/robotframework/robotframework/issues/4365
            # "Default Tags",  # Deprecated: https://github.com/robotframework/robotframework/issues/4365
            lang.keyword_tags_setting,  # New: https://github.com/robotframework/robotframework/issues/4373
            lang.library_setting,
            lang.resource_setting,
            lang.variables_setting,
        )


class _InitFileSettingsSection(Section):
    matches_rf_node_class = "SettingSection"
    markers = ("Setting", "Settings")
    names_in_brackets = False

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        names: Tuple[str, ...] = (
            "Documentation",
            "Metadata",
            "Suite Setup",
            "Suite Teardown",
            "Test Setup",
            "Test Teardown",
            "Test Timeout",
            "Library",
            "Resource",
            "Variables",
        )

        if get_robot_major_minor_version() >= (5, 1):
            names += ("Test Tags",)
        else:
            names += ("Force Tags",)
        return names

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.settings_header,)

    @classmethod
    def names_for_lang(cls, lang):
        # Only called in RF 5.1 onwards (so, we don't need to show deprecated names).
        return (
            lang.documentation_setting,
            lang.metadata_setting,
            lang.suite_setup_setting,
            lang.suite_teardown_setting,
            lang.test_setup_setting,
            lang.task_setup_setting,
            lang.test_teardown_setting,
            lang.task_teardown_setting,
            lang.test_timeout_setting,
            lang.task_timeout_setting,
            lang.test_tags_setting,  # In place of Force Tags
            lang.task_tags_setting,  # In place of Force Tags
            # "Force Tags",  # Deprecated: https://github.com/robotframework/robotframework/issues/4365
            lang.keyword_tags_setting,  # New: https://github.com/robotframework/robotframework/issues/4373
            lang.library_setting,
            lang.resource_setting,
            lang.variables_setting,
        )


class _ResourceFileSettingsSection(Section):
    matches_rf_node_class = "SettingSection"
    markers = ("Setting", "Settings")
    names_in_brackets = False

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return ("Documentation", "Library", "Resource", "Variables")

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.settings_header,)

    @classmethod
    def names_for_lang(cls, lang):
        return (
            lang.documentation_setting,
            lang.library_setting,
            lang.resource_setting,
            lang.variables_setting,
            lang.keyword_tags_setting,  # New: https://github.com/robotframework/robotframework/issues/4373
        )


class _VariableSection(Section):
    matches_rf_node_class = "VariableSection"
    markers = ("Variables", "Variable")

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.variables_header,)


class _TestCaseSection(Section):
    matches_rf_node_class = "TestCaseSection"
    markers = ("Test Cases", "Test Case", "Tasks", "Task")

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return ("Documentation", "Tags", "Setup", "Teardown", "Template", "Timeout")

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.tasks_header, lang.test_cases_header)

    @classmethod
    def names_for_lang(cls, lang):
        return (
            lang.documentation_setting,
            lang.tags_setting,
            lang.setup_setting,
            lang.teardown_setting,
            lang.template_setting,
            lang.timeout_setting,
        )


class _KeywordSection(Section):
    matches_rf_node_class = "KeywordSection"
    markers = ("Keywords", "Keyword")

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return ("Documentation", "Arguments", "Teardown", "Timeout", "Tags", "Return")

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.keywords_header,)

    @classmethod
    def names_for_lang(cls, lang):
        return (
            lang.documentation_setting,
            lang.arguments_setting,
            lang.teardown_setting,
            lang.timeout_setting,
            lang.tags_setting,
            "Return",  # No translation
        )


class _CommentSection(Section):
    matches_rf_node_class = "CommentSection"
    markers = ("Comment", "Comments")

    @classmethod
    def get_names_in_section_pre_rf_5_1(cls) -> Tuple[str, ...]:
        return ()

    @classmethod
    def markers_for_lang(cls, lang):
        return (lang.comments_header,)

    @classmethod
    def names_for_lang(cls, lang):
        return ()


# Sections that can appear in a test case
_TEST_CASE_FILE_SECTIONS = [
    _TestCaseFileSettingsSection,
    _VariableSection,
    _TestCaseSection,
    _KeywordSection,
    _CommentSection,
]

# Sections that can appear in an init file
_INIT_FILE_SECTIONS = [
    _InitFileSettingsSection,
    _VariableSection,
    _KeywordSection,
    _CommentSection,
]

# Sections that can appear in a resource file
_RESOURCE_FILE_SECTIONS = [
    _ResourceFileSettingsSection,
    _VariableSection,
    _KeywordSection,
    _CommentSection,
]


def _get_accepted_section_header_words(
    completion_context: ICompletionContext, accept_word: Callable[[Any, str], bool]
) -> List[str]:
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    sections = _get_accepted_sections(completion_context)
    ret = []
    if robot_version_supports_language():
        from robot.api import Language

        locinfo: ILocalizationInfo = completion_context.get_ast_localization_info()

        for section in sections:
            lang: Language
            for lang in locinfo.iter_languages_on_write():
                markers = section.markers_for_lang(lang)

                for marker in markers:
                    if accept_word(lang, marker):
                        ret.append(marker.title())
    else:
        for section in sections:
            for marker in section.markers:
                if accept_word(None, marker):
                    ret.append(marker.title())

    ret.sort()
    return ret


def _get_accepted_sections(completion_context) -> list:
    t = completion_context.get_type()
    if t == completion_context.TYPE_TEST_CASE:
        return _TEST_CASE_FILE_SECTIONS

    elif t == completion_context.TYPE_RESOURCE:
        return _RESOURCE_FILE_SECTIONS

    elif t == completion_context.TYPE_INIT:
        return _INIT_FILE_SECTIONS

    else:
        log.critical("Unrecognized section: %s", t)
        return _TEST_CASE_FILE_SECTIONS


def get_section_constant(completion_context, section: INode) -> Optional[Section]:
    accepted_sections = _get_accepted_sections(completion_context)

    for s in accepted_sections:
        if s.matches_rf_node_class == section.__class__.__name__:
            return s
    return None


# Default: accept only plural
def _accept_word_default(language, word):
    # Language is None on RF < 5.1
    if language is None:
        return word.endswith("s")

    # On RF 5.1 onwards the translation only requests translation
    # for the plural version. Note that this effectively removes
    # support for this setting on RF 5.1.
    return True


def complete(completion_context: ICompletionContext):
    from robocorp_ls_core.lsp import CompletionItemKind
    from robocorp_ls_core.lsp import CompletionItem
    from robocorp_ls_core.lsp import TextEdit
    from robocorp_ls_core.lsp import Range
    from robocorp_ls_core.lsp import Position
    from robotframework_ls.impl import text_utilities
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM,
    )
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL,
    )

    selection = completion_context.sel  #: :type selection: DocumentSelection
    line_start = selection.line_to_column
    items = []

    if line_start:
        tu = text_utilities.TextUtilities(line_start)

        if tu.strip_leading_chars("*"):  # i.e.: the line must start with '*'
            line_to_end = selection.line_to_end
            tu.strip()

            # On RF 5.1 onwards the translation only requests translation
            # for the plural version. Note that this effectively removes
            # support for this setting on RF 5.1.
            # We should deprecate it in the future...
            form = OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL
            config = completion_context.config
            if config is not None:
                form = config.get_setting(
                    OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM,
                    str,
                    OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL,
                )

            accept_word = _accept_word_default
            if form == "singular":

                def accept_word(language, word):  # noqa
                    if language is None:
                        return not word.endswith("s")
                    return True

            elif form == "both":

                def accept_word(language, word):  # noqa
                    return True

            words = _get_accepted_section_header_words(completion_context, accept_word)
            matcher = RobotStringMatcher(tu.text)

            # If we have a *, replace until that char (with it included)
            delta_to_replace = line_to_end.rfind("*") + 1
            if delta_to_replace == 0:
                for i, c in enumerate(line_to_end):
                    if c == "#":
                        # We want to preserve breaks
                        break

                    if c in (" ", "\t"):
                        continue

                    delta_to_replace = i + 1  # +1 to replace the char we just saw

            for word in words:
                if matcher.accepts(word):
                    label = "*** %s ***" % (word,)

                    text_edit = TextEdit(
                        Range(
                            # i.e.: always replace from the start of the line.
                            start=Position(selection.line, 0),
                            end=Position(
                                selection.line, selection.col + delta_to_replace
                            ),
                        ),
                        label,
                    )
                    # text_edit = None
                    items.append(
                        CompletionItem(
                            label,
                            kind=CompletionItemKind.Class,
                            text_edit=text_edit,
                            insertText=text_edit.newText,
                        )
                    )

    return [item.to_dict() for item in items]
