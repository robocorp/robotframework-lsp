def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.lsp import CompletionItemKind
    from robotframework_ls.lsp import CompletionItem
    from robotframework_ls.lsp import TextEdit
    from robotframework_ls.lsp import Range
    from robotframework_ls.lsp import Position
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
            tu.strip()

            words = completion_context.get_accepted_section_header_words()
            config = completion_context.config

            form = config.get_setting(
                OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM,
                str,
                OPTION_ROBOT_COMPLETION_SECTION_HEADERS_FORM_PLURAL,
            )
            matcher = RobotStringMatcher(tu.text)
            for word in words:
                if form == "plural":
                    if not word.endswith("s"):
                        continue
                elif form == "singular":
                    if word.endswith("s"):
                        continue
                if matcher.accepts(word):
                    label = "*** %s ***" % (word,)
                    text_edit = TextEdit(
                        Range(
                            # i.e.: always replace from the start of the line.
                            start=Position(selection.line, 0),
                            end=Position(selection.line, selection.col),
                        ),
                        label,
                    )
                    # text_edit = None
                    items.append(
                        CompletionItem(
                            label, kind=CompletionItemKind.Class, text_edit=text_edit
                        )
                    )

    return [item.to_dict() for item in items]
