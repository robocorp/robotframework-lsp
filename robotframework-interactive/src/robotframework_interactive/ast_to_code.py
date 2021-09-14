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
    for i, txt in enumerate(reversed(v.text)):
        if not txt.strip():
            continue
        else:
            break

    if i > 0:
        v.text = v.text[:-i]
        v.text.append("\n")

    return "".join(v.text)
