def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.lsp import (
        TextEdit,
        Range,
        Position,
        CompletionItem,
        CompletionItemKind,
    )
    from robotframework_ls.impl.string_matcher import StringMatcher

    ret = []

    # ast_utils.print_ast(ast)
    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = token_info.token
        if token.type == token.KEYWORD:
            selection = completion_context.sel  #: :type selection: DocumentSelection
            # We're in a context where we should complete keywords.
            libraries = completion_context.get_imported_libraries()
            library_names = [library.name for library in libraries]
            libspec_manager = completion_context.workspace.libspec_manager
            matcher = StringMatcher(token.value)
            for library_name in library_names:
                try:
                    library_info = libspec_manager.get_library_info(
                        library_name, create=True
                    )
                except KeyError:
                    pass
                else:
                    for keyword in library_info.keywords:
                        keyword_name = keyword.name
                        if matcher.accepts(keyword_name):
                            label = keyword_name
                            text_edit = TextEdit(
                                Range(
                                    start=Position(selection.line, token.col_offset),
                                    end=Position(selection.line, token.end_col_offset),
                                ),
                                label,
                            )
                            # text_edit = None
                            ret.append(
                                CompletionItem(
                                    label,
                                    kind=CompletionItemKind.Class,
                                    text_edit=text_edit,
                                ).to_dict()
                            )

    return ret
