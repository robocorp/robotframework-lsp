import os.path
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def _create_completion_item(library_name, selection, token, start_col_offset=None):
    from robocorp_ls_core.lsp import (
        CompletionItem,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
    from robocorp_ls_core.lsp import MarkupKind
    from robocorp_ls_core.lsp import CompletionItemKind

    text_edit = TextEdit(
        Range(
            start=Position(
                selection.line,
                start_col_offset if start_col_offset is not None else token.col_offset,
            ),
            end=Position(selection.line, token.end_col_offset),
        ),
        library_name,
    )

    # text_edit = None
    return CompletionItem(
        library_name,
        kind=CompletionItemKind.Module,
        text_edit=text_edit,
        insertText=text_edit.newText,
        documentation="",
        insertTextFormat=InsertTextFormat.Snippet,
        documentationFormat=MarkupKind.PlainText,
    ).to_dict()


def _add_completions_from_dir(
    completion_context,
    directory,
    matcher,
    ret,
    sel,
    token,
    qualifier,
    extensions,
    skip_current,
):
    from robocorp_ls_core import uris

    def normfile(path):
        return os.path.normpath(os.path.normcase(path))

    curr_file = normfile(uris.to_fs_path(completion_context.doc.uri))

    try:
        # This is ok if the directory doesn't exist.
        contents = sorted(os.listdir(directory))
    except:
        return

    for filename in contents:
        use_path = None
        if filename.endswith(extensions):
            # If that'd be a match for the current .robot file, don't show it.
            if skip_current and curr_file == normfile(
                os.path.join(directory, filename)
            ):
                continue

            use_path = filename

        elif filename not in ("__pycache__", ".git") and os.path.isdir(
            os.path.join(directory, filename)
        ):
            use_path = filename + "/"
        else:
            continue

        if matcher.accepts(use_path):

            ret.append(
                _create_completion_item(
                    use_path, sel, token, start_col_offset=sel.col - len(qualifier)
                )
            )


def _get_completions(completion_context, token, match_libs, extensions, skip_current):
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robocorp_ls_core import uris
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB, RESERVED_LIB

    ret = []

    sel = completion_context.sel
    value_to_cursor = token.value
    if token.end_col_offset > sel.col:
        value_to_cursor = value_to_cursor[: -(token.end_col_offset - sel.col)]
    if "{" in value_to_cursor:
        value_to_cursor = completion_context.token_value_resolving_variables(
            value_to_cursor
        )

    value_to_cursor_split = os.path.split(value_to_cursor)

    if os.path.isabs(value_to_cursor):
        _add_completions_from_dir(
            completion_context,
            value_to_cursor_split[0],
            RobotStringMatcher(value_to_cursor_split[1]),
            ret,
            sel,
            token,
            value_to_cursor_split[1],
            extensions,
            skip_current=skip_current,
        )

    else:
        if match_libs:
            matcher = RobotStringMatcher(value_to_cursor)
            libspec_manager = completion_context.workspace.libspec_manager
            library_names = set(libspec_manager.get_library_names())
            library_names.discard(BUILTIN_LIB)
            library_names.discard(RESERVED_LIB)

            for library_name in library_names:
                if matcher.accepts(library_name):
                    ret.append(_create_completion_item(library_name, sel, token))

        # After checking the existing library names in memory (because we
        # loaded them at least once), check libraries in the filesystem.
        uri = completion_context.doc.uri
        path = uris.to_fs_path(uri)
        dirname = os.path.dirname(path)

        matcher = RobotStringMatcher(value_to_cursor_split[1])
        directory = os.path.join(dirname, value_to_cursor_split[0])
        _add_completions_from_dir(
            completion_context,
            directory,
            matcher,
            ret,
            sel,
            token,
            value_to_cursor_split[1],
            extensions,
            skip_current=skip_current,
        )
    return ret


def _get_resource_completions(completion_context, token):
    return _get_completions(
        completion_context,
        token,
        False,
        (".resource", ".robot", ".txt"),
        skip_current=True,
    )


def _get_library_completions(completion_context, token):
    return _get_completions(
        completion_context, token, True, (".py",), skip_current=False
    )


def complete(completion_context):
    """
    Provides the completions for 'Library' and 'Resource' imports.
    
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl import ast_utils

    ret = []

    try:
        token_info = completion_context.get_current_token()
        if token_info is not None:
            token = ast_utils.get_library_import_name_token(
                token_info.node, token_info.token
            )
            if token is not None:
                ret = _get_library_completions(completion_context, token)
            else:
                token = ast_utils.get_resource_import_name_token(
                    token_info.node, token_info.token
                )
                if token is not None:
                    ret = _get_resource_completions(completion_context, token)

    except:
        log.exception()

    return ret
