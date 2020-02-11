def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.lsp import CompletionItemKind
    from robotframework_ls.lsp import CompletionItem
    from robotframework_ls.lsp import TextEdit
    from robotframework_ls.lsp import Range
    from robotframework_ls.lsp import Position
    from robotframework_ls.completions import text_utilities
    from robotframework_ls.completions.string_matcher import StringMatcher

    selection = completion_context.sel  #: :type selection: DocumentSelection
    current_line = selection.current_line
    if not current_line:
        return []

    words = ("Settings", "Variables", "Test Cases", "Tasks", "Keywords", "Comment")

    items = []

    line_start = current_line[: selection.col]

    if line_start:
        tu = text_utilities.TextUtilities(line_start)

        if tu.strip_leading_chars("*"):  # i.e.: the line must start with '*'
            tu.strip()

            matcher = StringMatcher(tu.text)
            for word in words:
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
                            label, kind=CompletionItemKind.Method, text_edit=text_edit
                        )
                    )

    return [item.to_dict() for item in items]
