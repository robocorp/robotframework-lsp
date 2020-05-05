import ast as ast_module
from robotframework_ls.lsp import Error
import sys
from collections import namedtuple
from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)


class _NodesProviderVisitor(ast_module.NodeVisitor):
    def __init__(self, on_node=lambda node: None):
        ast_module.NodeVisitor.__init__(self)
        self._stack = []
        self.on_node = on_node

    def generic_visit(self, node):
        self._stack.append(node)
        self.on_node(self._stack, node)
        ast_module.NodeVisitor.generic_visit(self, node)
        self._stack.pop()


class _PrinterVisitor(ast_module.NodeVisitor):
    def __init__(self, stream):
        ast_module.NodeVisitor.__init__(self)
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

            ret = ast_module.NodeVisitor.generic_visit(self, node)
        finally:
            self._level -= 1
        return ret


def collect_errors(node):
    """
    :return list(Error)
    """
    errors = []
    for _stack, node in _iter_nodes_filtered(node, accept_class="Error"):
        msg = node.error

        errors.append(create_error_from_node(node, msg))

    return errors


def create_error_from_node(node, msg, tokens=None):
    """
    :return Error:
    """
    if tokens is None:
        tokens = node.tokens

    if not tokens:
        log.log("No tokens found when visiting %s." % (node.__class__,))
        start = (0, 0)
        end = (0, 0)
    else:
        # line is 1-based and col is 0-based (make both 0-based for the error).
        start = (tokens[0].lineno - 1, tokens[0].col_offset)
        end = (tokens[-1].lineno - 1, tokens[-1].end_col_offset)

    error = Error(msg, start, end)
    return error


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

    for _field, value in ast_module.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast_module.AST):
                    yield stack, item
                    if recursive:
                        stack.append(item)
                        for o in _iter_nodes(item, stack, recursive=recursive):
                            yield o
                        stack.pop()
        elif isinstance(value, ast_module.AST):
            if recursive:
                yield stack, value
                stack.append(value)

                for o in _iter_nodes(value, stack, recursive=recursive):
                    yield o

                stack.pop()


_NodeInfo = namedtuple("_NodeInfo", "stack, node")
_TokenInfo = namedtuple("_TokenInfo", "stack, node, token")
_KeywordUsageInfo = namedtuple("_KeywordUsageInfo", "stack, node, token, name")


def find_token(ast, line, col):
    """
    :rtype: robotframework_ls.impl.ast_utils._TokenInfo|NoneType
    """
    for stack, node in _iter_nodes(ast):
        try:
            tokens = node.tokens
        except AttributeError:
            continue
        for token in tokens:
            lineno = token.lineno - 1
            if lineno != line:
                continue

            if token.type == token.SEPARATOR:
                # For separator tokens, it must be entirely within the section
                # i.e.: if it's in the boundary for a word, we want the word,
                # not the separator.
                if token.col_offset < col < token.end_col_offset:
                    return _TokenInfo(tuple(stack), node, token)
            else:
                if token.col_offset <= col <= token.end_col_offset:
                    return _TokenInfo(tuple(stack), node, token)


def _iter_nodes_filtered(ast, accept_class, recursive=True):
    """
    :rtype: generator(tuple(list,ast_module.AST))
    """
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)
    for stack, node in _iter_nodes(ast, recursive=recursive):
        if node.__class__.__name__ in accept_class:
            yield stack, node


def iter_library_imports(ast):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(ast, accept_class="LibraryImport"):
        yield _NodeInfo(tuple(stack), node)


def iter_resource_imports(ast):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(ast, accept_class="ResourceImport"):
        yield _NodeInfo(tuple(stack), node)


def iter_keywords(ast):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(ast, accept_class="Keyword"):
        yield _NodeInfo(tuple(stack), node)


def iter_variables(ast):
    """
    :rtype: generator(_NodeInfo)
    """
    for stack, node in _iter_nodes_filtered(ast, accept_class="Variable"):
        yield _NodeInfo(tuple(stack), node)


def iter_keyword_arguments_as_str(ast):
    """
    :rtype: generator(str)
    """
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Arguments"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                yield str(token)


def get_documentation(ast):
    doc = []
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Documentation"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                doc.append(str(token).strip())
    return "\n".join(doc)


def iter_keyword_usage_tokens(ast):
    """
    Iterates through all the places where a keyword name is being used, providing
    the stack, node, token and name.
    
    :return: generator(_KeywordUsageInfo)
    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    from robot.api import Token
    from robotframework_ls._utils import isinstance_name

    for stack, node in _iter_nodes(ast, recursive=True):
        if node.__class__.__name__ == "KeywordCall":
            token = _strip_token_bdd_prefix(node.get_token(Token.KEYWORD))
            node = _copy_of_node_replacing_token(node, token, Token.KEYWORD)
            keyword_name = token.value
            yield _KeywordUsageInfo(tuple(stack), node, token, keyword_name)

        elif isinstance_name(node, ("Fixture", "TestTemplate")):
            node, token = _strip_node_and_token_bdd_prefix(node, Token.NAME)
            keyword_name = token.value
            yield _KeywordUsageInfo(tuple(stack), node, token, keyword_name)


def get_keyword_name_token(ast, token):
    """
    :note: this goes hand-in-hand with iter_keyword_usage_tokens.
    """
    from robotframework_ls._utils import isinstance_name

    if token.type == token.KEYWORD or (
        token.type == token.NAME and isinstance_name(ast, ("Fixture", "TestTemplate"))
    ):
        return _strip_token_bdd_prefix(token)
    return None


def _copy_of_node_replacing_token(node, token, token_type):
    """
    Workaround to create a new version of the same node but with the first
    occurrence of a token of the given type changed to another token.
    """
    new_tokens = list(node.tokens)
    for i, t in enumerate(new_tokens):
        if t.type == token_type:
            new_tokens[i] = token
            break
    return node.__class__(new_tokens)


def _strip_node_and_token_bdd_prefix(node, token_type):
    """
    This is a workaround because the parsing does not separate a BDD prefix from
    the keyword name. If the parsing is improved to do that separation in the future
    we can stop doing this.
    """
    original_token = node.get_token(token_type)
    token = _strip_token_bdd_prefix(original_token)
    if token is original_token:
        # i.e.: No change was done.
        return node, token
    return _copy_of_node_replacing_token(node, token, token_type), token


def _strip_token_bdd_prefix(token):
    """
    This is a workaround because the parsing does not separate a BDD prefix from
    the keyword name. If the parsing is improved to do that separation in the future
    we can stop doing this.
    
    :return Token:
        Returns a new token with the bdd prefix stripped or the original token passed.
    """
    from robotframework_ls.impl.robot_constants import BDD_PREFIXES
    from robot.api import Token
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    text = normalize_robot_name(token.value)
    for prefix in BDD_PREFIXES:
        if text.startswith(prefix):
            new_name = token.value[len(prefix) :]
            return Token(
                type=token.type,
                value=new_name,
                lineno=token.lineno,
                col_offset=token.col_offset + len(prefix),
                error=token.error,
            )
    return token
