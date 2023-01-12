from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.lsp import TextEditTypedDict
from typing import List

log = get_logger(__name__)


def on_type_formatting(
    completion_context: ICompletionContext, ch: str
) -> List[TextEditTypedDict]:
    # Note: this isn't really integrated right now. The idea for on type
    # formatting would be that when the user types a new line it'd
    # apply code formatting for the previous line (the structure is in
    # place, but this isn't really done).
    #
    # Note: this happens after a given char was typed out (so, if we
    # handle '\n', the result of the '\n' will already be applied
    # to the document).

    # if ch == "\n":
    #     from robotframework_ls.impl import ast_utils
    #
    #     section = completion_context.get_ast_current_section()
    #     if section is None:
    #         return []
    #
    #     line = completion_context.sel.line
    #     col = completion_context.sel.col
    #     return [
    #         {
    #             "range": {
    #                 "start": {"line": line, "character": col},
    #                 "end": {"line": line, "character": col},
    #             },
    #             "newText": "...",
    #         }
    #     ]

    return []
