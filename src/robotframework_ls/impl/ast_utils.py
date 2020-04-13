import ast
from robotframework_ls.lsp import Error
import sys
from collections import namedtuple
from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)


class _NodesProviderVisitor(ast.NodeVisitor):
    def __init__(self, on_node=lambda node: None):
        ast.NodeVisitor.__init__(self)
        self._stack = []
        self.on_node = on_node

    def generic_visit(self, node):
        self._stack.append(node)
        self.on_node(self._stack, node)
        ast.NodeVisitor.generic_visit(self, node)
        self._stack.pop()


class _PrinterVisitor(ast.NodeVisitor):
    def __init__(self, stream):
        ast.NodeVisitor.__init__(self)
        self._level = 0
        self._stream = stream

    def _replace_spacing(self, txt):
        curr_len = len(txt)
        delta = 80 - curr_len
        return txt.replace("*SPACING*", " " * delta)

    def generic_visit(self, node):
        # Note: prints line and col offsets 0-based (even if the ast is 1-based for
        # lines and 0-based for columns).
        self._level += 1
        try:
            indent = "  " * self._level
            node_lineno = node.lineno
            if node_lineno != -1:
                # Make 0-based
                node_lineno -= 1
            node_end_lineno = node.end_lineno
            if node_end_lineno != -1:
                # Make 0-based
                node_end_lineno -= 1
            self._stream.write(
                self._replace_spacing(
                    "%s%s *SPACING* (%s, %s) -> (%s, %s)\n"
                    % (
                        indent,
                        node.__class__.__name__,
                        node_lineno,
                        node.col_offset,
                        node_end_lineno,
                        node.end_col_offset,
                    )
                )
            )
            tokens = getattr(node, "tokens", [])
            for token in tokens:

                token_lineno = token.lineno
                if token_lineno != -1:
                    # Make 0-based
                    token_lineno -= 1

                self._stream.write(
                    self._replace_spacing(
                        "%s- %s, '%s' *SPACING* (%s, %s->%s)\n"
                        % (
                            indent,
                            token.type,
                            token.value.replace("\n", "\\n").replace("\r", "\\r"),
                            token_lineno,
                            token.col_offset,
                            token.end_col_offset,
                        )
                    )
                )

            ret = ast.NodeVisitor.generic_visit(self, node)
        finally:
            self._level -= 1
        return ret


def collect_errors(node):
    """
    :return list(_Error)
    """
    errors = []
    for _stack, node in _iter_nodes_filtered(node, accept_class="Error"):
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

        errors.append(Error(msg, start, end))

    return errors


def print_ast(node, stream=None):
    if stream is None:
        stream = sys.stderr
    errors_visitor = _PrinterVisitor(stream)
    errors_visitor.visit(node)


def find_section(node, line):
    """
    :param line:
        0-based
    """
    last_section = None
    for section in node.sections:
        # section.lineno is 1-based.
        if (section.lineno - 1) <= line:
            last_section = section

        else:
            return last_section

    return last_section


def _iter_nodes(node, stack=None, recursive=True):
    """
    :note: the yielded stack is actually always the same (mutable) list, so,
    clients that want to return it somewhere else should create a copy.
    """
    if stack is None:
        stack = []

    for _field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield stack, item
                    if recursive:
                        stack.append(item)
                        for o in _iter_nodes(item, stack, recursive=recursive):
                            yield o
                        stack.pop()
        elif isinstance(value, ast.AST):
            if recursive:
                yield stack, value
                stack.append(value)

                for o in _iter_nodes(value, stack, recursive=recursive):
                    yield o

                stack.pop()


_NodeInfo = namedtuple("_NodeInfo", "stack, node")
_TokenInfo = namedtuple("_TokenInfo", "stack, node, token")


def find_token(node, line, col):
    """
    :rtype: robotframework_ls.impl.ast_utils._TokenInfo|NoneType
    """
    for stack, node in _iter_nodes(node):
        try:
            tokens = node.tokens
        except AttributeError:
            continue
        for token in tokens:
            lineno = token.lineno - 1
            if lineno != line:
                continue

            if token.col_offset <= col <= token.end_col_offset:
                return _TokenInfo(tuple(stack), node, token)


def _iter_nodes_filtered(node, accept_class, recursive=True):
    """
    :rtype: generator(tuple(list,ast.AST))
    """
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)
    for stack, node in _iter_nodes(node, recursive=recursive):
        if node.__class__.__name__ in accept_class:
            yield stack, node


def iter_library_imports(node):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(node, accept_class="LibraryImport"):
        yield _NodeInfo(tuple(stack), node)


def iter_resource_imports(node):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(node, accept_class="ResourceImport"):
        yield _NodeInfo(tuple(stack), node)


def iter_keywords(node):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(node, accept_class="Keyword"):
        yield _NodeInfo(tuple(stack), node)


def iter_keyword_arguments_as_str(node):
    """
    :rtype: generator(str)
    """
    for _stack, node in _iter_nodes_filtered(node, accept_class="Arguments"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                yield str(token)


def get_documentation(node):
    doc = []
    for _stack, node in _iter_nodes_filtered(node, accept_class="Documentation"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                doc.append(str(token).strip())
    return "\n".join(doc)
