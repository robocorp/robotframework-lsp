from typing import Set, Iterable, List

from robocorp_ls_core.lsp import Range, CodeActionTypedDict, TextEditTypedDict
from robotframework_ls.impl.protocols import ICompletionContext, IRobotToken
from robotframework_ls.impl._code_action_utils import wrap_edits_in_snippet


def code_action_others(
    completion_context: ICompletionContext,
    select_range: Range,
    only: Set[str],
) -> Iterable[CodeActionTypedDict]:
    from robocorp_ls_core.basic import isinstance_name

    if only and "assign.toVar" not in only:
        return

    if select_range.start != select_range.end:
        # This one is only done when no range is given.
        return

    token_info = completion_context.get_current_token()
    if not token_info:
        return

    if not isinstance_name(token_info.node, "KeywordCall"):
        return

    for keyword_token in token_info.node.tokens:
        if keyword_token.type == keyword_token.ASSIGN:
            return

        if keyword_token.type == keyword_token.KEYWORD:
            # Leave keyword_token in the namespace.
            break
    else:
        return

    from robotframework_ls.robot_config import get_arguments_separator

    sep = get_arguments_separator(completion_context)
    tok: IRobotToken = keyword_token

    text_edits: List[TextEditTypedDict] = [
        {
            "range": {
                "start": {"line": tok.lineno - 1, "character": tok.col_offset},
                "end": {"line": tok.lineno - 1, "character": tok.col_offset},
            },
            "newText": "${${0:variable}}=%s" % (sep,),
        }
    ]
    yield wrap_edits_in_snippet(
        completion_context, "Assign to variable", text_edits, "assign.toVar"
    )
