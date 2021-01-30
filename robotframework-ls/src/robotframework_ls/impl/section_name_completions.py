def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    import itertools
    from robocorp_ls_core.lsp import (
        TextEdit,
        Range,
        Position,
        CompletionItem,
        CompletionItemKind,
    )

    section_name = completion_context.get_current_section_name()
    if section_name:
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        section = completion_context.get_section(section_name)
        if section is not None:
            selection = completion_context.sel  #: :type selection: DocumentSelection
            line_to_col = selection.line_to_column
            if line_to_col.endswith("  "):
                return []
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
                        return []
                else:
                    return []

                matcher = RobotStringMatcher(line_to_col)

            else:
                # i.e.: Needs to be the first char
                matcher = RobotStringMatcher(line_to_col)
                replace_from_col = 0

            ret = []
            for word in sorted(itertools.chain(section.names, section.aliases)):
                if matcher.accepts(word):
                    if section.names_in_brackets:
                        label = "[%s]" % (word,)
                        line = selection.current_line
                        replacement = "[%s]" % (word,)
                        if line[selection.col :].startswith("]"):
                            replace_to_col += 1

                    else:
                        label = word
                        replacement = word

                    text_edit = TextEdit(
                        Range(
                            start=Position(selection.line, replace_from_col),
                            end=Position(selection.line, replace_to_col),
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

    return []
