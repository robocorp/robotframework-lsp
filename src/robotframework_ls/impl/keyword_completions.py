def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.lsp import (
        CompletionItem,
        CompletionItemKind,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robotframework_ls.impl.string_matcher import StringMatcher
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB
    from robotframework_ls.impl.robot_specbuilder import markdown_doc
    from robotframework_ls.lsp import MarkupKind

    ret = []

    # ast_utils.print_ast(ast)
    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = token_info.token
        if token.type == token.KEYWORD:
            selection = completion_context.sel  #: :type selection: DocumentSelection
            # We're in a context where we should complete keywords.
            libraries = completion_context.get_imported_libraries()
            library_names = set(library.name for library in libraries)
            library_names.add(BUILTIN_LIB)
            libspec_manager = completion_context.workspace.libspec_manager
            matcher = StringMatcher(token.value)
            for library_name in library_names:
                library_info = libspec_manager.get_library_info(
                    library_name, create=True
                )
                if library_info is not None:
                    #: :type keyword: KeywordDoc
                    for keyword in library_info.keywords:
                        keyword_name = keyword.name
                        if matcher.accepts(keyword_name):
                            label = keyword_name
                            text = label
                            if keyword.args:
                                for i, arg in enumerate(keyword.args):
                                    text += " ${%s:%s}" % (i + 1, arg)
                            text_edit = TextEdit(
                                Range(
                                    start=Position(selection.line, token.col_offset),
                                    end=Position(selection.line, token.end_col_offset),
                                ),
                                text,
                            )
                            # text_edit = None
                            ret.append(
                                CompletionItem(
                                    label,
                                    kind=CompletionItemKind.Class,
                                    text_edit=text_edit,
                                    documentation=markdown_doc(keyword),
                                    insertTextFormat=InsertTextFormat.Snippet,
                                    documentationFormat=MarkupKind.Markdown,
                                ).to_dict()
                            )

    return ret
