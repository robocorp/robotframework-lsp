def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    import itertools
    from robotframework_ls.lsp import (
        TextEdit,
        Range,
        Position,
        CompletionItem,
        CompletionItemKind,
    )
    from robotframework_ls.impl import ast_utils

    ret = []

    # ast_utils.print_ast(ast)
    token_info = completion_context.get_current_token()
    if token_info is not None:
        if token_info.token.type == token_info.token.KEYWORD:
            # We're in a context where we should complete keywords.
            libraries = completion_context.get_imported_libraries()
            library_names = [library.name for library in libraries]

    return ret
