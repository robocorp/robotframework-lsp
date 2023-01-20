from typing import Optional

from robocorp_ls_core.protocols import EvaluatableExpressionTypedDict
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotToken,
)


def _create_evaluatable_expression_from_token(
    token: IRobotToken, expression: str
) -> EvaluatableExpressionTypedDict:
    return {
        "range": {
            "start": {"line": token.lineno - 1, "character": token.col_offset},
            "end": {
                "line": token.lineno - 1,
                "character": token.end_col_offset,
            },
        },
        "expression": expression,
    }


def provide_evaluatable_expression(
    completion_context: ICompletionContext,
) -> Optional[EvaluatableExpressionTypedDict]:
    from robotframework_ls.impl import ast_utils

    var_token_info = completion_context.get_current_variable()
    if var_token_info is not None:
        token = var_token_info.token
        var_identifier = var_token_info.var_info.var_identifier
        if not var_identifier:
            var_identifier = "$"
        return _create_evaluatable_expression_from_token(
            token, var_identifier + "{" + token.value + "}"
        )

    token_info = completion_context.get_current_token()
    if token_info is not None:
        keyword_name_token = ast_utils.get_keyword_name_token(
            token_info.stack, token_info.node, token_info.token
        )
        if keyword_name_token is not None:
            return _create_evaluatable_expression_from_token(
                keyword_name_token, keyword_name_token.value
            )

    return None
