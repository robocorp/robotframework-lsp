import os.path
from robocorp_ls_core.robotframework_log import get_logger
from typing import Optional, List, Tuple
from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.lsp import CompletionItemTypedDict
from robocorp_ls_core.basic import normalize_filename
from robotframework_ls.impl.robot_constants import (
    ROBOT_AND_TXT_FILE_EXTENSIONS,
    LIBRARY_FILE_EXTENSIONS,
    VARIABLE_FILE_EXTENSIONS,
)

log = get_logger(__name__)


def _create_completion_item(
    library_name, selection, token, start_col_offset=None
) -> CompletionItemTypedDict:
    from robocorp_ls_core.lsp import (
        CompletionItem,
        InsertTextFormat,
        Position,
        Range,
        TextEdit,
    )
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
    ).to_dict()


def _add_completions_from_dir(
    completion_context,
    directory,
    matcher,
    ret: List[CompletionItemTypedDict],
    sel,
    token,
    qualifier,
    extensions,
    skip_current,
):
    from robocorp_ls_core import uris

    def normfile(path):
        return normalize_filename(path)

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


def _get_completions(
    completion_context: ICompletionContext,
    token,
    match_libs,
    extensions: Tuple[str, ...],
    skip_current: bool,
) -> List[CompletionItemTypedDict]:
    """
    :param skip_current:
        If we'd get a match for the current (.robot or .resource)
        file it will not be added.
    """
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robocorp_ls_core import uris
    from robotframework_ls.impl.robot_constants import BUILTIN_LIB, RESERVED_LIB
    from robotframework_ls.impl import ast_utils

    ret: List[CompletionItemTypedDict] = []

    sel = completion_context.sel
    value_to_cursor = token.value
    if token.end_col_offset > sel.col:
        value_to_cursor = value_to_cursor[: -(token.end_col_offset - sel.col)]
    if "{" in value_to_cursor:
        value_to_cursor = completion_context.token_value_resolving_variables(
            ast_utils.create_token(value_to_cursor)
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


def _get_resource_completions(
    completion_context, token
) -> List[CompletionItemTypedDict]:
    return _get_completions(
        completion_context,
        token,
        False,
        ROBOT_AND_TXT_FILE_EXTENSIONS,
        skip_current=True,
    )


def _get_library_completions(
    completion_context, token
) -> List[CompletionItemTypedDict]:
    return _get_completions(
        completion_context, token, True, LIBRARY_FILE_EXTENSIONS, skip_current=False
    )


def _get_variable_completions(
    completion_context, token
) -> List[CompletionItemTypedDict]:
    return _get_completions(
        completion_context,
        token,
        True,
        LIBRARY_FILE_EXTENSIONS + VARIABLE_FILE_EXTENSIONS,
        skip_current=False,
    )


class _Requisites(object):
    def __init__(self, token, found_type: str):
        self.token = token
        self._type = found_type

    @property
    def is_library(self):
        return self._type == "library"

    @property
    def is_resource(self):
        return self._type == "resource"

    @property
    def is_variables(self):
        return self._type == "variables"


def get_requisites(completion_context: ICompletionContext) -> Optional[_Requisites]:
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None:
        # Library
        token = ast_utils.get_library_import_name_token(
            token_info.node, token_info.token, generate_empty_on_eol=True
        )
        if token is not None:
            return _Requisites(token, "library")

        # Resource
        token = ast_utils.get_resource_import_name_token(
            token_info.node, token_info.token, generate_empty_on_eol=True
        )
        if token is not None:
            return _Requisites(token, "resource")

        # Variable
        token = ast_utils.get_variables_import_name_token(
            token_info.node, token_info.token, generate_empty_on_eol=True
        )
        if token is not None:
            return _Requisites(token, "variables")
    return None


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    """
    Provides the completions for 'Library', 'Resource' and 'Variables' imports.
    """
    try:
        requisites = get_requisites(completion_context)
        if requisites is None:
            return []

        return complete_with_requisites(completion_context, requisites)

    except:
        log.exception()

    return []


def complete_with_requisites(
    completion_context: ICompletionContext, requisites: _Requisites
) -> List[CompletionItemTypedDict]:
    try:
        if requisites.is_library:
            return _get_library_completions(completion_context, requisites.token)

        elif requisites.is_resource:
            return _get_resource_completions(completion_context, requisites.token)

        elif requisites.is_variables:
            return _get_variable_completions(completion_context, requisites.token)

    except:
        log.exception()

    return []
