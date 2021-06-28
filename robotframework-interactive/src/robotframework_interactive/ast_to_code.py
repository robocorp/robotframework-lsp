from robot.parsing.model.statements import Statement
import ast


class _Visitor(ast.NodeVisitor):
    def __init__(self, model):
        self.text = []
        self.visit(model)

    def visit(self, node):
        if isinstance(node, Statement):
            visitor = self.visit_Statement
        else:
            visitor = self.generic_visit
        visitor(node)

    def visit_Statement(self, node):  # noqa
        for token in node.tokens:
            self.text.append(token.value)


def ast_to_code(node):
    v = _Visitor(node)
    return "".join(v.text)
