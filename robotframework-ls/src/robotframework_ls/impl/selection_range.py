from robotframework_ls.impl.protocols import (
    ICompletionContext,
    TokenInfo,
    VarTokenInfo,
    IRobotToken,
    INode,
)
from robocorp_ls_core.lsp import (
    PositionTypedDict,
    SelectionRangeTypedDict,
)
from typing import List, Sequence
from robocorp_ls_core.robotframework_log import get_logger
import itertools

log = get_logger(__name__)


def _empty_range(position: PositionTypedDict) -> SelectionRangeTypedDict:
    line, col = position["line"], position["character"]
    r: SelectionRangeTypedDict = {
        "range": {
            "start": {
                "line": line,
                "character": col,
            },
            "end": {
                "line": line,
                "character": col,
            },
        }
    }
    return r


def _build_variable_range_hierarchy(
    current_token: TokenInfo,
    current_variable: VarTokenInfo,
) -> SelectionRangeTypedDict:
    from robotframework_ls.impl.ast_utils import create_range_from_token

    ret: SelectionRangeTypedDict = {
        "range": create_range_from_token(current_variable.token)
    }

    # The current token is the container of the current variable.
    current_token_selection_range = _build_token_range_hierarchy(current_token)
    if not current_token_selection_range.get("range"):
        return ret

    if current_token_selection_range.get("range") != ret["range"]:
        ret["parent"] = current_token_selection_range
    return ret


def _build_token_range_from_stack(
    ret: SelectionRangeTypedDict,
    current_node: INode,
    stack: Sequence[INode],
    token: IRobotToken,
):
    from robotframework_ls.impl.ast_utils import create_range_from_node

    last: SelectionRangeTypedDict = ret

    for stack_node in itertools.chain((current_node,), reversed(stack)):
        r = create_range_from_node(
            stack_node,
            accept_empty=token.type in (token.EOL, token.EOS, token.SEPARATOR),
        )
        if r is None:
            continue

        if last["range"] == r:  # If it's the same, don't add it.
            continue

        new_range: SelectionRangeTypedDict = {"range": r}
        last["parent"] = new_range
        last = new_range


def _build_token_range_hierarchy(current_token: TokenInfo) -> SelectionRangeTypedDict:
    from robotframework_ls.impl.ast_utils import create_range_from_token

    token = current_token.token
    ret: SelectionRangeTypedDict = {"range": create_range_from_token(token)}
    _build_token_range_from_stack(ret, current_token.node, current_token.stack, token)
    return ret


def selection_range(
    context: ICompletionContext, positions: List[PositionTypedDict]
) -> List[SelectionRangeTypedDict]:
    if not positions:
        return []

    ret: List[SelectionRangeTypedDict] = []

    from robotframework_ls.impl import ast_utils

    ast = context.get_ast()

    for position in positions:
        line = position["line"]
        section = ast_utils.find_section(ast, line)
        if section is None:
            ret.append(_empty_range(position))
            continue

        col = position["character"]

        current_token = ast_utils.find_token(section, line, col)
        if current_token is None:
            ret.append(_empty_range(position))
            continue

        current_variable = ast_utils.find_variable(section, line, col)
        if current_variable is not None:
            ret.append(_build_variable_range_hierarchy(current_token, current_variable))
            continue

        ret.append(_build_token_range_hierarchy(current_token))
    log.info("returning: %s", ret)
    return ret
