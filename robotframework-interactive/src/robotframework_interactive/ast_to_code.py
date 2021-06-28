from robot.api.parsing import ModelVisitor, Token


class _Visitor(ModelVisitor):
    def __init__(self, model):
        self.text = []
        self.visit(model)

    def visit_Statement(self, node):  # noqa
        for token in node.tokens:
            self.text.append(token.value)


def ast_to_code(node):
    v = _Visitor(node)
    return "".join(v.text)
