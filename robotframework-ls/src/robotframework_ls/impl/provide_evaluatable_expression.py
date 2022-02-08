from robotframework_ls.impl.protocols import (
    ICompletionContext,
    EvaluatableExpressionTypedDict,
)
from typing import Optional


def _create_evaluatable_expression_from_token(token) -> EvaluatableExpressionTypedDict:
    return {
        "range": {
            "start": {"line": token.lineno - 1, "character": token.col_offset},
            "end": {
                "line": token.lineno - 1,
                "character": token.end_col_offset,
            },
        },
        "expression": token.value,
    }


def provide_evaluatable_expression(
    completion_context: ICompletionContext,
) -> Optional[EvaluatableExpressionTypedDict]:
    from robotframework_ls.impl.text_utilities import is_variable_text
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_variable()
    if token_info is not None:
        token = token_info.token
        if is_variable_text(token.value):
            return _create_evaluatable_expression_from_token(token)

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = ast_utils.get_keyword_name_token(token_info.node, token_info.token)
        if token is not None:
            return _create_evaluatable_expression_from_token(token)

    return None
