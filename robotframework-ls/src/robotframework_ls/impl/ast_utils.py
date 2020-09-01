import ast as ast_module
from robocorp_ls_core.lsp import Error
import sys
from collections import namedtuple
from robocorp_ls_core.robotframework_log import get_logger

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


def find_variable(ast, line, col):
    token_info = find_token(ast, line, col)
    if token_info is not None:
        token = token_info.token
        if "{" in token.value:
            for part in _tokenize_variables_even_when_invalid(token, col):
                if part.col_offset <= col <= part.end_col_offset:
                    if part.type == part.VARIABLE:
                        return _TokenInfo(token_info.stack, token_info.node, part)
                    else:
                        return None
            else:
                return None
    return None


def create_token(name):
    from robot.api import Token

    return Token(Token.NAME, name)


def tokenize_variables_from_name(name):
    return tokenize_variables(create_token(name))  # May throw error if it's not OK.


def tokenize_variables(token):
    return token.tokenize_variables()  # May throw error if it's not OK.


def _tokenize_variables_even_when_invalid(token, col):
    """
    If Token.tokenize_variables() fails, this can still provide the variable under
    the given column by appliying some heuristics to find open variables.
    """
    try:
        return token.tokenize_variables()
    except:
        pass

    # If we got here, it means that we weren't able to tokenize the variables
    # properly (probably some variable wasn't closed properly), so, let's do
    # a custom implementation for this use case.

    from robot.api import Token
    from robotframework_ls.impl.robot_constants import VARIABLE_PREFIXES

    diff = col - token.col_offset
    up_to_cursor = token.value[:diff]
    open_at = up_to_cursor.rfind("{")

    if open_at >= 1:
        if up_to_cursor[open_at - 1] in VARIABLE_PREFIXES:
            varname = [up_to_cursor[open_at - 1 :]]
            from_cursor = token.value[diff:]

            for c in from_cursor:
                if c in VARIABLE_PREFIXES or c.isspace() or c == "{":
                    break
                if c == "}":
                    varname.append(c)
                    break
                varname.append(c)

            return [
                Token(
                    type=token.VARIABLE,
                    value="".join(varname),
                    lineno=token.lineno,
                    col_offset=token.col_offset + open_at - 1,
                    error=token.error,
                )
            ]


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
    for token in iter_keyword_arguments_as_tokens(ast):
        yield str(token)


def iter_keyword_arguments_as_tokens(ast):
    """
    :rtype: generator(Token)
    """
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Arguments"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                yield token


def get_documentation(ast):
    doc = []
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Documentation"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                doc.append(str(token).strip())
    return "\n".join(doc)


def iter_variable_assigns(ast):
    from robot.api import Token

    for stack, node in _iter_nodes(ast, recursive=False):
        if node.__class__.__name__ == "KeywordCall":
            for token in node.get_tokens(Token.ASSIGN):
                value = token.value
                i = value.rfind("}")
                if i > 0:
                    new_value = value[: i + 1]
                    token = Token(
                        type=token.type,
                        value=new_value,
                        lineno=token.lineno,
                        col_offset=token.col_offset,
                        error=token.error,
                    )

                yield _TokenInfo(tuple(stack), node, token)


def iter_keyword_usage_tokens(ast):
    """
    Iterates through all the places where a keyword name is being used, providing
    the stack, node, token and name.
    
    :return: generator(_KeywordUsageInfo)
    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    from robot.api import Token
    from robocorp_ls_core.basic import isinstance_name

    for stack, node in _iter_nodes(ast, recursive=True):
        if node.__class__.__name__ == "KeywordCall":
            token = _strip_token_bdd_prefix(node.get_token(Token.KEYWORD))
            if token is not None:
                node = _copy_of_node_replacing_token(node, token, Token.KEYWORD)
                keyword_name = token.value
                yield _KeywordUsageInfo(tuple(stack), node, token, keyword_name)

        elif isinstance_name(node, ("Fixture", "TestTemplate")):
            node, token = _strip_node_and_token_bdd_prefix(node, Token.NAME)
            keyword_name = token.value
            yield _KeywordUsageInfo(tuple(stack), node, token, keyword_name)


def get_keyword_name_token(ast, token):
    """
    If the given token is a keyword, return the token, otherwise return None.
    
    :note: this goes hand-in-hand with iter_keyword_usage_tokens.
    """
    from robocorp_ls_core.basic import isinstance_name

    if token.type == token.KEYWORD or (
        token.type == token.NAME and isinstance_name(ast, ("Fixture", "TestTemplate"))
    ):
        return _strip_token_bdd_prefix(token)
    return None


def get_library_import_name_token(ast, token):
    """
    If the given ast node is a library import and the token is its name, return
    the name token, otherwise, return None.
    """
    from robocorp_ls_core.basic import isinstance_name

    if (
        token.type == token.NAME
        and isinstance_name(ast, "LibraryImport")
        and ast.name == token.value  # I.e.: match the name, not the alias.
    ):
        return token
    return None


def get_resource_import_name_token(ast, token):
    """
    If the given ast node is a library import and the token is its name, return
    the name token, otherwise, return None.
    """
    from robocorp_ls_core.basic import isinstance_name

    if (
        token.type == token.NAME
        and isinstance_name(ast, "ResourceImport")
        and ast.name == token.value  # I.e.: match the name, not the alias.
    ):
        return token
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

    if token is None:
        return token

    text = token.value.lower()
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
