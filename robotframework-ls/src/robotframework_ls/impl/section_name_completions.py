from robotframework_ls.impl.protocols import ICompletionContext, ILocalizationInfo
from typing import Optional
from robotframework_ls.impl.text_utilities import normalize_robot_name


class _Requisites(object):
    def __init__(self, section, matcher, replace_from_col, replace_to_col, selection):
        self.section = section
        self.matcher = matcher
        self.replace_from_col = replace_from_col
        self.replace_to_col = replace_to_col
        self.selection = selection


def get_requisites(completion_context: ICompletionContext) -> Optional[_Requisites]:
    section_node = completion_context.get_ast_current_section()
    if section_node is None:
        return None

    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.section_completions import get_section_constant

    section = get_section_constant(completion_context, section_node)
    if section is None:
        return None

    selection = completion_context.sel  #: :type selection: DocumentSelection
    line_to_col = selection.line_to_column
    if line_to_col.endswith("  "):
        return None
    replace_to_col = selection.col
    if section.names_in_brackets:
        for i, c in enumerate(line_to_col):
            if c.isspace():
                continue
            elif c == "[":
                line_to_col = line_to_col[i + 1 :]
                replace_from_col = i
                break
            else:
                return None
        else:
            return None

        matcher = RobotStringMatcher(line_to_col)

    else:
        # i.e.: Needs to be the first char
        matcher = RobotStringMatcher(line_to_col)
        replace_from_col = 0

    return _Requisites(section, matcher, replace_from_col, replace_to_col, selection)


def complete(completion_context: ICompletionContext):
    from robocorp_ls_core.lsp import (
        TextEdit,
        Range,
        Position,
        CompletionItem,
        CompletionItemKind,
    )
    from robotframework_ls.impl.robot_version import robot_version_supports_language

    requisites = get_requisites(completion_context)
    if requisites is None:
        return []

    section = requisites.section
    matcher = requisites.matcher
    replace_from_col = requisites.replace_from_col
    selection = requisites.selection
    replace_to_col = requisites.replace_to_col

    line = selection.current_line
    sel_ends_with_close = line[selection.col :].startswith("]")

    ret = []
    if robot_version_supports_language():
        from robot.api import Language

        locinfo: ILocalizationInfo = completion_context.get_ast_localization_info()
        current_section_name = normalize_robot_name(
            completion_context.get_current_section_name()
        )

        def _translated_words():
            lang: Language
            for lang in locinfo.iter_languages_on_write():
                markers = section.markers_for_lang(lang)
                for marker in markers:
                    if normalize_robot_name(marker) == current_section_name:
                        yield from iter(section.names_for_lang(lang))
                        return

            # If it didn't return (is this possible?), provide all.
            for lang in locinfo.iter_languages_on_write():
                yield from iter(section.names_for_lang(lang))

        words = tuple(_translated_words())

    else:
        words = section.get_names_in_section_pre_rf_5_1()

    for word in sorted(words):
        if matcher.accepts(word):
            col_delta = 0
            if section.names_in_brackets:
                label = f"[{word}]"
                replacement = label
                if sel_ends_with_close:
                    col_delta = 1

            else:
                label = word
                replacement = word

            text_edit = TextEdit(
                Range(
                    start=Position(selection.line, replace_from_col),
                    end=Position(selection.line, replace_to_col + col_delta),
                ),
                replacement,
            )
            # text_edit = None
            ret.append(
                CompletionItem(
                    label, kind=CompletionItemKind.Keyword, text_edit=text_edit
                ).to_dict()
            )

    return ret
