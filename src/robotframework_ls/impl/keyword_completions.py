import os.path
import logging

log = logging.getLogger(__name__)


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


def _collect_completions_from_ast(ast, completion_context, token, matcher, ret):
    from robotframework_ls.impl import ast_utils

    for keyword in ast_utils.iter_keywords(ast):
        keyword_name = keyword.node.name
        if matcher.accepts(keyword_name):
            args = []
            for arg in ast_utils.iter_keyword_arguments_as_str(keyword.node):
                args.append(arg)
            # TODO: Get docs
            docs_format = "markdown"
            docs = ast_utils.get_documentation(keyword.node)
            ret.append(
                _create_completion_item_from_keyword(
                    keyword_name, args, docs_format, docs, completion_context.sel, token
                )
            )


def _append_current_doc_keywords(completion_context, token, matcher, ret):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, token, matcher, ret)


def _append_libraries_keywords(completion_context, token, matcher, ret):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords from libraries
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB
    from robotframework_ls.impl.robot_specbuilder import docs_and_format

    libraries = completion_context.get_imported_libraries()
    library_names = set(library.name for library in libraries)
    library_names.add(BUILTIN_LIB)
    libspec_manager = completion_context.workspace.libspec_manager

    for library_name in library_names:
        library_info = libspec_manager.get_library_info(library_name, create=True)
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
                            completion_context.sel,
                            token,
                        )
                    )


def _append_resource_imports_keywords(completion_context, token, matcher, ret):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls import uris

    # Get keywords from resources
    resource_imports = completion_context.get_resource_imports()
    for resource_import in resource_imports:
        for token in resource_import.tokens:
            if token.type == token.NAME:
                parts = []
                for v in token.tokenize_variables():
                    if v.type == v.NAME:
                        parts.append(str(v))

                    elif v.type == v.VARIABLE:
                        # Resolve variable from config
                        v = str(v)
                        if v.startswith("${") and v.endswith("}"):
                            v = v[2:-1]
                            parts.append(completion_context.convert_robot_variable(v))
                        else:
                            log.info("Cannot resolve variable: %s", v)

                resource_path = "".join(parts)
                if not os.path.isabs(resource_path):
                    # It's a relative resource, resolve its location based on the
                    # current file.
                    resource_path = os.path.join(
                        os.path.dirname(completion_context.doc.path), resource_path
                    )

                ws = completion_context.workspace
                if not os.path.exists(resource_path):
                    log.info("Resource not found: %s", resource_path)
                    continue

                doc_uri = uris.from_fs_path(resource_path)

                resource_doc = ws.get_document(doc_uri, create=False)
                if resource_doc is None:
                    resource_doc = ws.create_untracked_document(doc_uri)

                ast = resource_doc.get_ast()
                _collect_completions_from_ast(
                    ast, completion_context, token, matcher, ret
                )


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl.string_matcher import StringMatcher

    ret = []

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = token_info.token
        if token.type == token.KEYWORD:
            # We're in a context where we should complete keywords.

            matcher = StringMatcher(token.value)

            _append_current_doc_keywords(completion_context, token, matcher, ret)

            _append_resource_imports_keywords(completion_context, token, matcher, ret)

            _append_libraries_keywords(completion_context, token, matcher, ret)

    return ret
