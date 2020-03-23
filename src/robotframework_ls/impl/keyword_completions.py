def _create_completion_item_from_keyword(
    keyword_name, args, docs_format, docs, selection, token
):
    from robotframework_ls.lsp import (
        CompletionItem,
        CompletionItemKind,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robotframework_ls.lsp import MarkupKind

    label = keyword_name
    text = label

    for i, arg in enumerate(args):
        text += " ${%s:%s}" % (i + 1, arg)

    text_edit = TextEdit(
        Range(
            start=Position(selection.line, token.col_offset),
            end=Position(selection.line, token.end_col_offset),
        ),
        text,
    )

    # text_edit = None
    return CompletionItem(
        keyword_name,
        kind=CompletionItemKind.Class,
        text_edit=text_edit,
        documentation=docs,
        insertTextFormat=InsertTextFormat.Snippet,
        documentationFormat=(
            MarkupKind.Markdown if docs_format == "markdown" else MarkupKind.PlainText
        ),
    ).to_dict()


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl.string_matcher import StringMatcher
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB
    from robotframework_ls.impl.robot_specbuilder import docs_and_format

    ret = []

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = token_info.token
        if token.type == token.KEYWORD:
            selection = completion_context.sel  #: :type selection: DocumentSelection
            matcher = StringMatcher(token.value)

            # Get keywords defined in the file itself
            from robotframework_ls.impl import ast_utils

            ast = completion_context.get_ast()
            for keyword in ast_utils.iter_keywords(ast):
                keyword_name = keyword.node.name
                if matcher.accepts(keyword_name):
                    args = []
                    for arg in ast_utils.iter_keyword_arguments_as_str(keyword.node):
                        args.append(arg)
                    docs_format = "markdown"
                    docs = ""
                    ret.append(
                        _create_completion_item_from_keyword(
                            keyword_name, args, docs_format, docs, selection, token
                        )
                    )

            # We're in a context where we should complete keywords.
            libraries = completion_context.get_imported_libraries()
            library_names = set(library.name for library in libraries)
            library_names.add(BUILTIN_LIB)
            libspec_manager = completion_context.workspace.libspec_manager

            for library_name in library_names:
                library_info = libspec_manager.get_library_info(
                    library_name, create=True
                )
                if library_info is not None:
                    #: :type keyword: KeywordDoc
                    for keyword in library_info.keywords:
                        keyword_name = keyword.name
                        if matcher.accepts(keyword_name):
                            args = []
                            if keyword.args:
                                args = keyword.args
                            docs, docs_format = docs_and_format(keyword)

                            ret.append(
                                _create_completion_item_from_keyword(
                                    keyword_name,
                                    args,
                                    docs_format,
                                    docs,
                                    selection,
                                    token,
                                )
                            )

    return ret
