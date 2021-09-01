import sys
from typing import Iterator, Optional, List, Tuple, Any, Union

import ast as ast_module
from robocorp_ls_core.lsp import Error
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    TokenInfo,
    NodeInfo,
    KeywordUsageInfo,
    ILibraryImportNode,
)
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robocorp_ls_core.basic import isinstance_name
from robotframework_ls.impl.keywords_in_args import KEYWORD_NAME_TO_KEYWORD_INDEX


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

            ast_module.NodeVisitor.generic_visit(self, node)
        finally:
            self._level -= 1


MAX_ERRORS = 100


def _get_errors_from_tokens(node):
    for token in node.tokens:
        if token.type in (token.ERROR, token.FATAL_ERROR):
            start = (token.lineno - 1, token.col_offset)
            end = (token.lineno - 1, token.end_col_offset)
            error = Error(token.error, start, end)
            yield error


def collect_errors(node) -> List[Error]:
    errors = []

    use_errors_attribute = "errors" in node.__class__._attributes

    for _stack, node in _iter_nodes(node, recursive=True):
        if node.__class__.__name__ == "Error":
            errors.extend(_get_errors_from_tokens(node))

        elif use_errors_attribute:
            node_errors = getattr(node, "errors", ())
            if node_errors:
                for error in node_errors:
                    errors.append(create_error_from_node(node, error, tokens=[node]))

        if len(errors) >= MAX_ERRORS:
            break

    return errors


def create_error_from_node(node, msg, tokens=None) -> Error:
    if tokens is None:
        tokens = node.tokens

    if not tokens:
        log.info("No tokens found when visiting: %s.", node.__class__)
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


def find_section(node, line: int):
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


def find_token(ast, line, col) -> Optional[TokenInfo]:
    for stack, node in _iter_nodes(ast):
        try:
            tokens = node.tokens
        except AttributeError:
            continue

        last_token = None
        for token in tokens:
            lineno = token.lineno - 1
            if lineno != line:
                continue

            if token.type == token.SEPARATOR:
                # For separator tokens, it must be entirely within the section
                # i.e.: if it's in the boundary for a word, we want the word,
                # not the separator.
                if token.col_offset < col < token.end_col_offset:
                    return TokenInfo(tuple(stack), node, token)

            elif token.type == token.EOL:
                # A trailing whitespace after a keyword should be part of
                # the keyword, not EOL.
                if token.col_offset <= col <= token.end_col_offset:
                    diff = col - token.col_offset
                    if last_token is not None and not token.value.strip():
                        eol_contents = token.value[:diff]
                        if len(eol_contents) <= 1:
                            token = _append_eol_to_prev_token(last_token, eol_contents)

                    return TokenInfo(tuple(stack), node, token)

            else:
                if token.col_offset <= col <= token.end_col_offset:
                    return TokenInfo(tuple(stack), node, token)

            last_token = token

    return None


def find_variable(ast, line, col) -> Optional[TokenInfo]:
    token_info = find_token(ast, line, col)
    if token_info is not None:
        token = token_info.token
        if "{" in token.value:
            parts = _tokenize_variables_even_when_invalid(token, col)
            if not parts:
                return None

            for part in parts:
                if part.col_offset <= col <= part.end_col_offset:
                    if part.type == part.VARIABLE:
                        return TokenInfo(token_info.stack, token_info.node, part)
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


def _iter_nodes_filtered(
    ast, accept_class: Union[Tuple[str, ...], str], recursive=True
) -> Iterator[Tuple[list, Any]]:
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)
    for stack, node in _iter_nodes(ast, recursive=recursive):
        if node.__class__.__name__ in accept_class:
            yield stack, node


LIBRARY_IMPORT_CLASSES = ("LibraryImport",)
RESOURCE_IMPORT_CLASSES = ("ResourceImport",)
SETTING_SECTION_CLASSES = ("SettingSection",)


def iter_nodes(
    ast, accept_class: Union[Tuple[str, ...], str], recursive=True
) -> Iterator[NodeInfo]:
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)
    for stack, node in _iter_nodes(ast, recursive=recursive):
        if node.__class__.__name__ in accept_class:
            yield NodeInfo(tuple(stack), node)


def iter_all_nodes(ast, recursive=True) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes(ast, recursive=recursive):
        yield NodeInfo(tuple(stack), node)


def is_library_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in LIBRARY_IMPORT_CLASSES


def is_resource_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in RESOURCE_IMPORT_CLASSES


def is_setting_section_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in SETTING_SECTION_CLASSES


def iter_library_imports(ast) -> Iterator[NodeInfo[ILibraryImportNode]]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="LibraryImport"):
        yield NodeInfo(tuple(stack), node)


def iter_resource_imports(ast) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="ResourceImport"):
        yield NodeInfo(tuple(stack), node)


def iter_variable_imports(ast) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="VariablesImport"):
        yield NodeInfo(tuple(stack), node)


def iter_keywords(ast) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="Keyword"):
        yield NodeInfo(tuple(stack), node)


def iter_variables(ast) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="Variable"):
        yield NodeInfo(tuple(stack), node)


def iter_tests(ast) -> Iterator[NodeInfo]:
    for stack, node in _iter_nodes_filtered(ast, accept_class="TestCase"):
        yield NodeInfo(tuple(stack), node)


def iter_test_case_sections(ast) -> Iterator[NodeInfo]:
    # Sections are top-level, so, we don't need to do it recursively.
    for stack, node in _iter_nodes_filtered(
        ast, accept_class="TestCaseSection", recursive=False
    ):
        yield NodeInfo(tuple(stack), node)


def iter_keyword_arguments_as_str(ast) -> Iterator[str]:
    for token in iter_keyword_arguments_as_tokens(ast):
        yield str(token)


def iter_keyword_arguments_as_tokens(ast) -> Iterator:
    """
    :rtype: generator(Token)
    """
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Arguments"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                yield token


def get_documentation(ast) -> str:
    doc = []
    for _stack, node in _iter_nodes_filtered(ast, accept_class="Documentation"):
        for token in node.tokens:
            if token.type == token.ARGUMENT:
                doc.append(str(token).strip())
    return "\n".join(doc)


def iter_variable_assigns(ast) -> Iterator:
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

                yield TokenInfo(tuple(stack), node, token)


def iter_keyword_usage_tokens(
    ast, collect_args_as_keywords: bool
) -> Iterator[KeywordUsageInfo]:
    """
    Iterates through all the places where a keyword name is being used, providing
    the stack, node, token and name.
    """

    for stack, node in _iter_nodes(ast, recursive=True):
        usage_info = _create_keyword_usage_info(stack, node)
        if usage_info is not None:
            yield usage_info

            if collect_args_as_keywords:
                for token in usage_info.node.tokens:
                    if is_argument_keyword_name(usage_info.node, token):
                        yield KeywordUsageInfo(
                            usage_info.stack, usage_info.node, token, token.value
                        )


def _create_keyword_usage_info(stack, node) -> Optional[KeywordUsageInfo]:
    """
    If this is a keyword usage node, return information on it, otherwise, 
    returns None.
    
    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    from robot.api import Token

    if node.__class__.__name__ == "KeywordCall":
        token = _strip_token_bdd_prefix(node.get_token(Token.KEYWORD))
        if token is not None:
            node = _copy_of_node_replacing_token(node, token, Token.KEYWORD)
            keyword_name = token.value
            return KeywordUsageInfo(tuple(stack), node, token, keyword_name)

    elif isinstance_name(node, ("Fixture", "TestTemplate")):
        node, token = _strip_node_and_token_bdd_prefix(node, Token.NAME)
        if token is not None:
            keyword_name = token.value
            return KeywordUsageInfo(tuple(stack), node, token, keyword_name)

    return None


def create_keyword_usage_info_from_token(
    stack, node, token
) -> Optional[KeywordUsageInfo]:
    """
    If this is a keyword usage node, return information on it, otherwise, 
    returns None.
    
    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    if is_argument_keyword_name(node, token):
        return KeywordUsageInfo(tuple(stack), node, token, token.value)

    return _create_keyword_usage_info(stack, node)


def is_argument_keyword_name(node, token) -> bool:
    if isinstance_name(node, "KeywordCall"):
        consider_keyword_at_index = KEYWORD_NAME_TO_KEYWORD_INDEX.get(
            normalize_robot_name(node.keyword)
        )
        if consider_keyword_at_index is not None:
            i_arg = 0
            for arg in node.tokens:
                if arg.type == token.ARGUMENT:
                    i_arg += 1
                    if arg is token:
                        if i_arg == consider_keyword_at_index:
                            return True
    return False


def get_keyword_name_token(ast, token):
    """
    If the given token is a keyword, return the token, otherwise return None.
    
    :note: this goes hand-in-hand with iter_keyword_usage_tokens.
    """
    if token.type == token.KEYWORD or (
        token.type == token.NAME and isinstance_name(ast, ("Fixture", "TestTemplate"))
    ):
        return _strip_token_bdd_prefix(token)

    if token.type == token.ARGUMENT and not token.value.strip().endswith("}"):
        if is_argument_keyword_name(ast, token):
            return token

    return None


def get_library_import_name_token(ast, token):
    """
    If the given ast node is a library import and the token is its name, return
    the name token, otherwise, return None.
    """

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

    if (
        token.type == token.NAME
        and isinstance_name(ast, "ResourceImport")
        and ast.name == token.value  # I.e.: match the name, not the alias.
    ):
        return token
    return None


def get_variables_import_name_token(ast, token):
    """
    If the given ast node is a variables import and the token is its name, return
    the name token, otherwise, return None.
    """

    if (
        token.type == token.NAME
        and isinstance_name(ast, "VariablesImport")
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
    if original_token is None:
        return node, None
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


def _append_eol_to_prev_token(last_token, eol_token_contents):
    from robot.api import Token

    new_value = last_token.value + eol_token_contents

    return Token(
        type=last_token.type,
        value=new_value,
        lineno=last_token.lineno,
        col_offset=last_token.col_offset,
        error=last_token.error,
    )


def create_range_from_token(token):
    from robocorp_ls_core.lsp import RangeTypedDict, PositionTypedDict

    start: PositionTypedDict = {"line": token.lineno - 1, "character": token.col_offset}
    end: PositionTypedDict = {
        "line": token.lineno - 1,
        "character": token.end_col_offset,
    }
    code_lens_range: RangeTypedDict = {"start": start, "end": end}
    return code_lens_range
