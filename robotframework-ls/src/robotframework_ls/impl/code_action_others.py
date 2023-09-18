from typing import Set, Iterable, List

from robocorp_ls_core.lsp import Range, CodeActionTypedDict, TextEditTypedDict
from robotframework_ls.impl.protocols import ICompletionContext, IRobotToken
from robotframework_ls.impl._code_action_utils import wrap_edits_in_snippet
from robocorp_ls_core.protocols import IDocument


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


def code_action_surround_with(
    completion_context: ICompletionContext,
    select_range: Range,
    only: Set[str],
) -> Iterable[CodeActionTypedDict]:
    from robotframework_ls.impl.robot_version import get_robot_major_version

    if (
        only
        and "surroundWith.tryExcept" not in only
        and "surroundWith.tryExceptFinally" not in only
    ):
        return

    if select_range.start == select_range.end:
        # This one requires a selection.
        return

    if get_robot_major_version() < 5:
        return  # Requires RF 5.

    line = select_range.start.line
    col = select_range.start.character
    endline = select_range.end.line
    endcol = select_range.end.character

    doc: IDocument = completion_context.doc
    contents = doc.get_range(line, col, endline, endcol)
    first_line_contents = doc.get_line(line)
    last_line_contents = doc.get_line(endline)

    if line == endline:
        # If the selection is only at one line, verify whether all contents are
        # selected.
        if first_line_contents.strip() != contents.strip():
            return

    from robotframework_ls.impl.text_utilities import TextUtilities
    from robotframework_ls.robot_config import get_arguments_separator

    sep = get_arguments_separator(completion_context)
    indent = None
    lines = []
    for line_i in range(line, endline + 1):
        line_content = doc.get_line(line_i)
        if not line_content.strip().startswith("#"):
            new_indent = TextUtilities(line_content).get_indent()
            if indent is None:
                indent = new_indent
            else:
                if len(new_indent) < len(indent):
                    indent = new_indent

        lines.append(line_content)

    if not indent:
        return

    if not only or "surroundWith.tryExcept" in only:
        # Try..except
        full_lines = []
        full_lines.append(f"{indent}TRY")
        for line_content in lines:
            full_lines.append(f"{indent}{line_content}")
        full_lines.append(f"{indent}EXCEPT{sep}${{0:message}}")
        full_lines.append(f"{indent}{sep}No operation")
        full_lines.append(f"{indent}END")

        text_edits: List[TextEditTypedDict] = [
            {
                "range": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": endline, "character": len(last_line_contents)},
                },
                "newText": "\n".join(full_lines),
            }
        ]
        yield wrap_edits_in_snippet(
            completion_context,
            "Surround with try..except",
            text_edits,
            "surroundWith.tryExcept",
        )

    if not only or "surroundWith.tryExceptFinally" in only:
        # Try..except..finally
        full_lines = []
        full_lines.append(f"{indent}TRY")
        for line_content in lines:
            full_lines.append(f"{indent}{line_content}")
        full_lines.append(f"{indent}EXCEPT{sep}${{0:message}}")
        full_lines.append(f"{indent}{sep}No operation")
        full_lines.append(f"{indent}FINALLY")
        full_lines.append(f"{indent}{sep}No operation")
        full_lines.append(f"{indent}END")

        text_edits = [
            {
                "range": {
                    "start": {"line": line, "character": 0},
                    "end": {"line": endline, "character": len(last_line_contents)},
                },
                "newText": "\n".join(full_lines),
            }
        ]
        yield wrap_edits_in_snippet(
            completion_context,
            "Surround with try..except..finally",
            text_edits,
            "surroundWith.tryExceptFinally",
        )
