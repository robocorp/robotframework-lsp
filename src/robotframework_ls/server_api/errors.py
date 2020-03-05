import logging
import ast
from robotframework_ls.lsp import DiagnosticSeverity

log = logging.getLogger(__name__)


class Error(object):

    __slots__ = "msg start end".split(" ")

    def __init__(self, msg, start, end):
        """
        Note: `start` and `end` are tuples with (line, col).
        """
        self.msg = msg
        self.start = start
        self.end = end

    def to_dict(self):
        return dict((name, getattr(self, name)) for name in self.__slots__)

    def __repr__(self):
        import json

        return json.dumps(self.to_dict())

    __str__ = __repr__

    def to_lsp_diagnostic(self):
        return {
            "range": {
                "start": {"line": self.start[0], "character": self.start[1]},
                "end": {"line": self.end[0], "character": self.end[1]},
            },
            "severity": DiagnosticSeverity.Error,
            "source": "robotframework",
            "message": self.msg,
        }


class ErrorsVisitor(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        ast.NodeVisitor.__init__(self, *args, **kwargs)
        self.errors = []

    def visit_Error(self, node):
        tokens = node.tokens
        msg = node.error

        if not tokens:
            log.log("No tokens found when visiting error.")
            start = (0, 0)
            end = (0, 0)
        else:
            # line is 1-based and col is 0-based (make both 0-based for the error).
            start = (tokens[0].lineno - 1, tokens[0].col_offset)

            # If we only have one token make the error cover the whole line.
            end = (start[0] + 1, 0)

            if len(tokens) > 1:
                end = (tokens[-1].lineno - 1, tokens[-1].col_offset)

        self.errors.append(Error(msg, start, end))


def collect_errors(source):
    """
    :return list(Error)
    """
    from robot.parsing import get_model

    model = get_model(source)

    errors_visitor = ErrorsVisitor()
    errors_visitor.visit(model)
    return errors_visitor.errors
