from robot.api.parsing import ModelTransformer, Token, End, Comment, EmptyLine

from robotidy.decorators import check_start_end_line


class AddMissingEnd(ModelTransformer):
    """
    Add missing END token to FOR loops and IF statements.

    Following code:

        FOR    ${x}    IN    foo    bar
            Log    ${x}

    will be transformed to:

        FOR    ${x}    IN    foo    bar
            Log    ${x}
        END

    Supports global formatting params: ``--startline`` and ``--endline``.
    """

    @check_start_end_line
    def visit_For(self, node):  # noqa
        self.generic_visit(node)
        self.fix_header_name(node, Token.FOR)
        outside = []
        if not node.end:  # fix statement position only if END was missing
            node.body, outside = self.collect_inside_statements(node)
        self.fix_end(node)
        return (node, *outside)

    @check_start_end_line
    def visit_If(self, node):  # noqa
        self.generic_visit(node)
        self.fix_header_name(node, node.type)
        if node.type != Token.IF:
            return node
        node.body, outside = self.collect_inside_statements(node)
        if node.orelse:
            orelse = node.orelse
            while orelse.orelse:
                orelse = orelse.orelse
            orelse.body, outside_orelse = self.collect_inside_statements(orelse)
            outside += outside_orelse
        self.fix_end(node)
        return (node, *outside)

    def fix_end(self, node):
        """Fix END (missing END, End -> END, END position should be the same as FOR etc)."""
        if node.header.tokens[0].type == Token.SEPARATOR:
            indent = node.header.tokens[0]
        else:
            indent = Token(Token.SEPARATOR, self.formatting_config.separator)
        node.end = End([indent, Token(Token.END, "END"), Token(Token.EOL)])

    @staticmethod
    def fix_header_name(node, header_name):
        node.header.data_tokens[0].value = header_name

    def collect_inside_statements(self, node):
        """Split statements from node for those that belong to it and outside nodes.

        In this example with missing END:
            FOR  ${i}  IN RANGE  10
                Keyword
            Other Keyword

        RF will store 'Other Keyword' inside FOR block even if it should be outside.
        """
        new_body = [[], []]
        is_outside = False
        starting_col = self.get_column(node)
        for child in node.body:
            if not isinstance(child, EmptyLine) and self.get_column(child) <= starting_col:
                is_outside = True
            new_body[is_outside].append(child)
        while new_body[0] and isinstance(new_body[0][-1], EmptyLine):
            new_body[1].insert(0, new_body[0].pop())
        return new_body

    @staticmethod
    def get_column(node):
        if hasattr(node, "header"):
            return node.header.data_tokens[0].col_offset
        if isinstance(node, Comment):
            token = node.get_token(Token.COMMENT)
            return token.col_offset
        if not node.data_tokens:
            return node.col_offset
        return node.data_tokens[0].col_offset

    @staticmethod
    def get_last_or_else(node):
        if not node.orelse:
            return None
        orelse = node.orelse
        while orelse.orelse:
            orelse = orelse.orelse
        return orelse
