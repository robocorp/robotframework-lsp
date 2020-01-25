import logging
import ast
from collections import namedtuple

log = logging.getLogger(__name__)

Error = namedtuple("Error", "msg, start, end")
"""
Note: `start` and `end` are tuples with (line, col) -- both are 0-based.
`end` may be None.
"""


class ErrorsVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)
        self.errors = []

    def visit_Error(self, node):
        tokens = node.tokens
        if not tokens:
            log.log("No tokens found when visiting error.")
            return

        msg = node.error
        # line is 1-based and col is 0-based (make both 0-based for the error).
        start = (tokens[0].lineno - 1, tokens[0].col_offset)
        end = None

        if len(tokens) > 1:
            end = (tokens[-1].lineno - 1, tokens[-1].col_offset)

        self.errors.append(Error(msg, start, end))


def collect_errors(source):
    """
    :return list(Error)
    """
    from robot.parsing.builders import get_model

    # TODO: Check if we should provide a curdir.
    model = get_model(source, curdir=None)

    errors_visitor = ErrorsVisitor()
    errors_visitor.visit(model)
    return errors_visitor.errors
