from typing import Set, Iterable, Any, List

from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    IRobotToken,
)
from robocorp_ls_core.lsp import (
    Range,
    TextEditTypedDict,
    CodeActionTypedDict,
)
from robotframework_ls.impl._code_action_utils import wrap_edits_in_snippet


def _create_local_variable_refactoring(
    completion_context: ICompletionContext,
    select_range: Range,
) -> Iterable[CodeActionTypedDict]:
    doc: IRobotDocument = completion_context.doc

    line = select_range.start.line
    col = select_range.start.character
    endline = select_range.end.line
    endcol = select_range.end.character

    if line == endline and col != endcol:
        contents = doc.get_range(line, col, endline, endcol)

        token_info = completion_context.get_current_token()
        if token_info:
            curr_node_line_0_based = token_info.node.lineno - 1
            from robotframework_ls.robot_config import get_arguments_separator
            from robotframework_ls.robot_config import (
                create_convert_keyword_format_func,
            )
            import re

            format_name = create_convert_keyword_format_func(completion_context.config)
            set_var_name = format_name("Set Variable")
            indent = "    "
            line_contents = completion_context.doc.get_line(curr_node_line_0_based)
            found = re.match("[\s]+", line_contents)
            if found:
                indent = found.group()

            sep = get_arguments_separator(completion_context)

            tok: IRobotToken = token_info.token
            changes: List[TextEditTypedDict] = [
                {
                    "range": {
                        "start": {"line": curr_node_line_0_based, "character": 0},
                        "end": {"line": curr_node_line_0_based, "character": 0},
                    },
                    "newText": "%s${${0:variable}}=%s%s%s%s\n"
                    % (indent, sep, set_var_name, sep, contents),
                },
                {
                    "range": {
                        "start": {"line": tok.lineno - 1, "character": col},
                        "end": {
                            "line": tok.lineno - 1,
                            "character": endcol,
                        },
                    },
                    "newText": "${${0:variable}}",
                },
            ]
            yield wrap_edits_in_snippet(
                completion_context,
                "Extract local variable",
                changes,
                "refactor.extract",
            )


def _create_variable_section_refactoring(
    completion_context: ICompletionContext,
    select_range: Range,
) -> Iterable[CodeActionTypedDict]:
    line = select_range.start.line
    col = select_range.start.character
    endline = select_range.end.line
    endcol = select_range.end.character

    if line == endline and col != endcol:
        token_info = completion_context.get_current_token()
        if token_info:
            from robotframework_ls.robot_config import get_arguments_separator
            from robotframework_ls.impl.code_action_common import (
                create_var_in_variables_section_text_edit,
            )

            doc = completion_context.doc
            contents = doc.get_range(line, col, endline, endcol)

            sep = get_arguments_separator(completion_context)
            var_template = "${${0:variable}}%s%s\n" % (
                sep,
                contents,
            )

            tok: IRobotToken = token_info.token
            text_edit = create_var_in_variables_section_text_edit(
                completion_context, var_template
            )
            changes: List[TextEditTypedDict] = [
                text_edit,
                {
                    "range": {
                        "start": {"line": tok.lineno - 1, "character": col},
                        "end": {
                            "line": tok.lineno - 1,
                            "character": endcol,
                        },
                    },
                    "newText": "${${0:variable}}",
                },
            ]
            yield wrap_edits_in_snippet(
                completion_context,
                "Extract variable to variable section",
                changes,
                "refactor.extract",
            )


def code_action_refactoring(
    completion_context: ICompletionContext,
    select_range: Range,
    only: Set[str],
) -> Iterable[CodeActionTypedDict]:
    """
    Used to do refactorings.
    """
    from robotframework_ls.impl import ast_utils

    current_section: Any = completion_context.get_ast_current_section()
    if ast_utils.is_keyword_section(current_section) or ast_utils.is_testcase_section(
        current_section
    ):
        if not only or (
            only
            and (
                "refactor" in only
                or "refactor.extract" in only
                or "refactor.extract.local" in only
            )
        ):
            yield from _create_local_variable_refactoring(
                completion_context, select_range
            )

        if not only or (
            only
            and (
                "refactor" in only
                or "refactor.extract" in only
                or "refactor.extract.variableSection" in only
            )
        ):
            yield from _create_variable_section_refactoring(
                completion_context, select_range
            )
