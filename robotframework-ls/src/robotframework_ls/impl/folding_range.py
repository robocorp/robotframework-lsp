from typing import List

from robocorp_ls_core.lsp import FoldingRangeTypedDict
from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def folding_range(
    completion_context: ICompletionContext,
) -> List[FoldingRangeTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.protocols import NodeInfo

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[FoldingRangeTypedDict] = []
    node: NodeInfo

    # i.e.: any node that spans more than one line
    # should be added to the result.
    for node in ast_utils.iter_all_nodes(ast):
        completion_context.check_cancelled()
        try:
            start_line = node.node.lineno - 1
            end_line = node.node.end_lineno - 1
            if end_line > start_line:
                ret.append({"startLine": start_line, "endLine": end_line})
        except Exception:
            log.exception("Error computing range")

    return ret
