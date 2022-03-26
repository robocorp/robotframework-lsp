import sys
from typing import (
    Iterator,
    Optional,
    List,
    Tuple,
    Any,
    Union,
    Hashable,
    Callable,
    Dict,
    Iterable,
)

import ast as ast_module
from robocorp_ls_core.lsp import Error, RangeTypedDict, PositionTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    TokenInfo,
    NodeInfo,
    KeywordUsageInfo,
    ILibraryImportNode,
    IRobotToken,
    INode,
    IRobotVariableMatch,
    VarTokenInfo,
    IKeywordArg,
)
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robocorp_ls_core.basic import isinstance_name
from robotframework_ls.impl.keywords_in_args import (
    KEYWORD_NAME_TO_KEYWORD_INDEX,
    KEYWORD_NAME_TO_CONDITION_INDEX,
)
import functools
import weakref
import threading
import typing


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


class _AbstractIndexer:
    def iter_indexed(self, clsname):
        pass

    @property
    def ast(self):
        return self._weak_ast()


class _FullIndexer(_AbstractIndexer):
    def __init__(self, weak_ast: "weakref.ref[ast_module.AST]"):
        self._weak_ast = weak_ast
        self._lock = threading.Lock()
        self._name_to_node_info_lst: Dict[str, List[NodeInfo]] = {}
        self._indexed_full = False

    def _index(self):
        with self._lock:
            if self._indexed_full:
                return

            ast = self._weak_ast()
            if ast is None:
                raise RuntimeError("AST already garbage collected.")

            for stack, node in _iter_nodes(ast):
                lst = self._name_to_node_info_lst.get(node.__class__.__name__)
                if lst is None:
                    lst = self._name_to_node_info_lst[node.__class__.__name__] = []

                lst.append(NodeInfo(tuple(stack), node))
            self._indexed_full = True

    def iter_indexed(self, clsname: str) -> Iterator[NodeInfo]:
        if not self._indexed_full:
            self._index()

        yield from iter(self._name_to_node_info_lst.get(clsname, ()))


class _SectionIndexer(_AbstractIndexer):
    """
    This is a bit smarter in that it can index only the parts we're interested
    in (so, to get the LibraryImport it won't iterate over the keywords to
    do the indexing).
    """

    INNER_INSIDE_TOP_LEVEL = {
        "LibraryImport": "SettingSection",
        "ResourceImport": "SettingSection",
        "VariablesImport": "SettingSection",
        "SuiteSetup": "SettingSection",
        "SuiteTeardown": "SettingSection",
        "TestTemplate": "SettingSection",
        # Not settings:
        "Keyword": "KeywordSection",
        "TestCase": "TestCaseSection",
        "Variable": "VariableSection",
    }

    TOP_LEVEL = {
        "SettingSection",
        "VariableSection",
        "TestCaseSection",
        "KeywordSection",
        "CommentSection",
    }

    def __init__(self, weak_ast):
        self._weak_ast = weak_ast
        self._lock = threading.Lock()
        self._first_level_name_to_node_info_lst: Dict[str, List[NodeInfo]] = {}

        # We always start by indexing the first level in this case (to get the sections
        # such as 'CommentSection', 'SettingSection', etc), which should be fast.

        ast = self._weak_ast()
        if ast is None:
            raise RuntimeError("AST already garbage collected.")

        for stack, node in _iter_nodes(ast, recursive=False):
            lst = self._first_level_name_to_node_info_lst.get(node.__class__.__name__)
            if lst is None:
                lst = self._first_level_name_to_node_info_lst[
                    node.__class__.__name__
                ] = []

            lst.append(NodeInfo(tuple(stack), node))

    def iter_indexed(self, clsname: str) -> Iterator[NodeInfo]:
        top_level = self.INNER_INSIDE_TOP_LEVEL.get(clsname)
        if top_level is not None:
            lst = self._first_level_name_to_node_info_lst.get(top_level)
            if lst is not None:
                for node_info in lst:
                    indexer = _obtain_ast_indexer(node_info.node)
                    yield from indexer.iter_indexed(clsname)
        else:
            if clsname in self.TOP_LEVEL:
                yield from iter(
                    self._first_level_name_to_node_info_lst.get(clsname, ())
                )
            else:
                # i.e.: We don't know what we should be getting, so, just check
                # everything...
                for lst in self._first_level_name_to_node_info_lst.values():
                    for node_info in lst:
                        indexer = _obtain_ast_indexer(node_info.node)
                        yield from indexer.iter_indexed(clsname)


class _ASTIndexer(_AbstractIndexer):
    def __init__(self, ast: ast_module.AST):
        self._weak_ast = weakref.ref(ast)
        self._is_root = ast.__class__.__name__ == "File"

        self._indexer: _AbstractIndexer
        if self._is_root:
            # Cache by sections
            self._indexer = _SectionIndexer(self._weak_ast)
        else:
            # Always cache fully
            self._indexer = _FullIndexer(self._weak_ast)

        self._additional_caches: Dict[Hashable, Tuple[Any, ...]] = {}

    def iter_cached(
        self, cache_key: Hashable, compute: Callable, *args
    ) -> Iterator[Any]:
        try:
            cached = self._additional_caches[cache_key]
        except KeyError:
            cached = tuple(compute(self, *args))
            self._additional_caches[cache_key] = cached

        yield from iter(cached)

    def iter_indexed(self, clsname: str) -> Iterator[NodeInfo]:
        return self._indexer.iter_indexed(clsname)


def _get_errors_from_tokens(node):
    for token in node.tokens:
        if token.type in (token.ERROR, token.FATAL_ERROR):
            start = (token.lineno - 1, token.col_offset)
            end = (token.lineno - 1, token.end_col_offset)
            error = Error(token.error, start, end)
            yield error


def _obtain_ast_indexer(ast):
    try:
        indexer = ast.__ast_indexer__
    except:
        indexer = ast.__ast_indexer__ = _ASTIndexer(ast)
    return indexer


def _convert_ast_to_indexer(func):
    @functools.wraps(func)
    def new_func(ast, *args, **kwargs):
        try:
            indexer = ast.__ast_indexer__
        except:
            indexer = ast.__ast_indexer__ = _ASTIndexer(ast)

        return func(indexer, *args, **kwargs)

    return new_func


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


def find_section(node, line: int) -> Optional[INode]:
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


if typing.TYPE_CHECKING:
    # The INode has Robot Framework specific methods, but at runtime
    # we can just check the actual ast class.
    from typing import runtime_checkable, Protocol

    @runtime_checkable
    class _AST_CLASS(INode, Protocol):
        pass


else:
    # We know that the AST we're dealing with is the INode.
    # We can't use runtime_checkable on Python 3.7 though.
    _AST_CLASS = ast_module.AST


def _iter_nodes(
    node, internal_stack: Optional[List[INode]] = None, recursive=True
) -> Iterator[Tuple[List[INode], INode]]:
    """
    :note: the yielded stack is actually always the same (mutable) list, so,
    clients that want to return it somewhere else should create a copy.
    """
    stack: List[INode]
    if internal_stack is None:
        stack = []
    else:
        stack = internal_stack

    if recursive:
        for _field, value in ast_module.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, _AST_CLASS):
                        yield stack, item
                        stack.append(item)
                        yield from _iter_nodes(item, stack, recursive=True)
                        stack.pop()

            elif isinstance(value, _AST_CLASS):
                yield stack, value
                stack.append(value)

                yield from _iter_nodes(value, stack, recursive=True)

                stack.pop()
    else:
        # Not recursive
        for _field, value in ast_module.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, _AST_CLASS):
                        yield stack, item

            elif isinstance(value, _AST_CLASS):
                yield stack, value


def iter_all_nodes_recursive(node: INode) -> Iterator[Tuple[List[INode], INode]]:
    """
    This function will iterate over all the nodes. Use only if there's no
    other way to implement it as iterating over all the nodes is slow...
    """
    yield from _iter_nodes(node)


def _iter_nodes_filtered_not_recursive(
    ast, accept_class: Union[Tuple[str, ...], str]
) -> Iterator[Tuple[list, Any]]:
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)
    for stack, node in _iter_nodes(ast, recursive=False):
        if node.__class__.__name__ in accept_class:
            yield stack, node


def find_token(section, line, col) -> Optional[TokenInfo]:
    """
    :param section:
        The result from find_section(line, col), to pre-filter the nodes we may match.
    """
    for stack, node in _iter_nodes(section):
        try:
            tokens = node.tokens
        except AttributeError:
            continue

        if not tokens:
            continue

        if (tokens[-1].lineno - 1) < line:
            # i.e.: if the last node in the token is still before the
            # line we're searching, keep on going
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


def _find_subvar(stack, node, initial_token, col) -> Optional[VarTokenInfo]:
    for token, var_identifier in _tokenize_subvars(initial_token):
        if token.col_offset <= col <= token.end_col_offset:
            return VarTokenInfo(stack, node, token, var_identifier)

    from robotframework_ls.impl import robot_constants

    for p in robot_constants.VARIABLE_PREFIXES:
        if initial_token.value.startswith(p + "{"):
            if initial_token.value.endswith("}"):
                var_token = copy_token_with_subpart(initial_token, 2, -1)
            else:
                var_token = copy_token_with_subpart(
                    initial_token, 2, len(initial_token.value)
                )

            var_identifier = p
            return VarTokenInfo(stack, node, var_token, var_identifier)
    return None


def find_variable(section, line, col) -> Optional[VarTokenInfo]:
    """
    Finds the current variable token. Note that it won't include '{' nor '}'.
    The token may also be an empty token if we have a variable without contents.
    """

    token_info = find_token(section, line, col)
    if token_info is not None:
        stack = token_info.stack
        node = token_info.node
        token = token_info.token

        try:
            if (
                token.type == token.ARGUMENT
                and node.__class__.__name__ in CLASSES_WTH_EXPRESSION_ARGUMENTS
            ):
                for part in iter_expression_variables(token):
                    if part.type == token.VARIABLE:
                        if part.col_offset <= col <= part.end_col_offset:
                            return VarTokenInfo(
                                stack, node, part, "$", VarTokenInfo.CONTEXT_EXPRESSION
                            )

                if "$" in token.value:
                    char_in_token = col - token.col_offset
                    if char_in_token >= 0:
                        value_up_to_cursor = token.value[:char_in_token]
                        if value_up_to_cursor.endswith("$"):
                            # Empty variable at this point
                            from robot.api import Token

                            empty_token = Token(
                                type=token.VARIABLE,
                                value="",
                                lineno=token.lineno,
                                col_offset=col,
                            )

                            return VarTokenInfo(
                                stack,
                                node,
                                empty_token,
                                "$",
                                VarTokenInfo.CONTEXT_EXPRESSION,
                            )

        except:
            log.exception("Unable to tokenize: %s", token)

        if "{" in token.value:
            parts = _tokenize_variables_even_when_invalid(token, col)
            if not parts:
                return None

            for part in parts:
                if part.type in (part.VARIABLE, part.ASSIGN):
                    if part.col_offset <= col <= part.end_col_offset:
                        return _find_subvar(
                            token_info.stack, token_info.node, part, col
                        )
            else:
                return None
    return None


def tokenize_variables_from_name(name):
    return tokenize_variables(create_token(name))  # May throw error if it's not OK.


def tokenize_variables(token: IRobotToken):
    return token.tokenize_variables()  # May throw error if it's not OK.


def _tokenize_variables_even_when_invalid(token: IRobotToken, col: int):
    """
    If Token.tokenize_variables() fails, this can still provide the variable under
    the given column by applying some heuristics to find open variables.
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


LIBRARY_IMPORT_CLASSES = ("LibraryImport",)
RESOURCE_IMPORT_CLASSES = ("ResourceImport",)
SETTING_SECTION_CLASSES = ("SettingSection",)


@_convert_ast_to_indexer
def iter_nodes(ast, accept_class: Union[Tuple[str, ...], str]) -> Iterator[NodeInfo]:
    """
    Note: always recursive.
    """
    if not isinstance(accept_class, (list, tuple, set)):
        accept_class = (accept_class,)

    for classname in accept_class:
        yield from ast.iter_indexed(classname)


def iter_all_nodes(ast, recursive=True) -> Iterator[NodeInfo]:
    """
    Note: use this *very* sparingly as no caching will take place
    (as all nodes need to be iterated).

    Use one of the filtered APIs whenever possible as those are cached
    by the type.
    """
    for stack, node in _iter_nodes(ast, recursive=recursive):
        yield NodeInfo(tuple(stack), node)


def is_library_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in LIBRARY_IMPORT_CLASSES


def is_resource_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in RESOURCE_IMPORT_CLASSES


def is_setting_section_node_info(node_info: NodeInfo) -> bool:
    return node_info.node.__class__.__name__ in SETTING_SECTION_CLASSES


@_convert_ast_to_indexer
def iter_library_imports(ast) -> Iterator[NodeInfo[ILibraryImportNode]]:
    yield from ast.iter_indexed("LibraryImport")


@_convert_ast_to_indexer
def iter_resource_imports(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("ResourceImport")


@_convert_ast_to_indexer
def iter_variable_imports(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("VariablesImport")


@_convert_ast_to_indexer
def iter_keywords(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("Keyword")


@_convert_ast_to_indexer
def iter_variables(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("Variable")


@_convert_ast_to_indexer
def iter_tests(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("TestCase")


@_convert_ast_to_indexer
def iter_test_case_sections(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("TestCaseSection")


@_convert_ast_to_indexer
def iter_setting_sections(ast) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed("SettingSection")


@_convert_ast_to_indexer
def iter_indexed(ast, clsname) -> Iterator[NodeInfo]:
    yield from ast.iter_indexed(clsname)


def iter_keyword_arguments_as_str(ast, tokenize_keyword_name=False) -> Iterator[str]:
    """
    Provides the arguments with the full representation (use only for getting
    docs).

    May return strings as:
    ${my.store}=${my.load}[first][second]
    """
    for token in _iter_keyword_arguments_tokens(ast, tokenize_keyword_name):
        yield token.value


@_convert_ast_to_indexer
def _iter_keyword_arguments_tokens(
    ast, tokenize_keyword_name=False
) -> Iterator[Tuple[IRobotToken, str]]:
    """
    This API provides tokens as they are.

    i.e.: it returns tokens as: ${my.store}=${my.load}[first][second]

    So, this is internal as the outer world is tailored to
    dealing with what's actually needed.
    """
    for node_info in ast.iter_indexed("Arguments"):
        for token in node_info.node.tokens:
            if token.type == token.ARGUMENT:
                yield token

    if tokenize_keyword_name:
        from robot.api import Token

        ast_node = ast.ast
        if ast_node.__class__.__name__ == "Keyword":
            keyword_name = ast_node.header.get_token(Token.KEYWORD_NAME)
            if keyword_name:
                try:
                    tokenized_vars = keyword_name.tokenize_variables()
                except:
                    pass
                else:
                    for tok in tokenized_vars:
                        if tok.type == Token.VARIABLE:
                            yield tok


def iter_keyword_arguments_as_tokens(
    ast, tokenize_keyword_name=False
) -> Iterator[Tuple[IRobotToken, str]]:
    """
    API tailored at getting argument names.

    It converts an argument such as:
    ${my.store}=${my.load}[first][second]

    and yields something as:

    my.store
    """
    for token in _iter_keyword_arguments_tokens(ast, tokenize_keyword_name):
        for t in _tokenize_subvars(token):
            # The first one is the variable store (the other is the
            # variable load on a default argument)
            # We are only interested in the former in this API.
            yield t
            break  # Just break the inner for.


def iter_keyword_arguments_as_kwarg(
    ast, tokenize_keyword_name=False
) -> Iterator[IKeywordArg]:

    from robotframework_ls.impl.robot_specbuilder import KeywordArg

    for token in _iter_keyword_arguments_tokens(ast, tokenize_keyword_name):
        yield KeywordArg(token.value)


def is_deprecated(ast) -> bool:
    from robotframework_ls.impl.text_utilities import has_deprecated_text

    docs = get_documentation_raw(ast)
    return has_deprecated_text(docs)


def get_documentation_raw(ast: INode) -> str:
    iter_in: Iterator[INode]
    if ast.__class__.__name__ == "File":
        # Handle the case where the File is given (docs must be gotten from
        # the *** Settings *** in this case).
        iter_in = (node_info.node for node_info in iter_setting_sections(ast))
    else:
        iter_in = iter((ast,))

    doc: List[str] = []
    last_line: List[str] = []

    last_token = None
    for ast_node in iter_in:
        for _stack, node in _iter_nodes_filtered_not_recursive(
            ast_node, accept_class="Documentation"
        ):
            for token in node.tokens:
                if last_token is not None and last_token.lineno != token.lineno:
                    doc.extend(last_line)
                    del last_line[:]

                last_token = token

                if token.type in (token.CONTINUATION, token.DOCUMENTATION):
                    # Ignore anything before a continuation.
                    del last_line[:]
                    continue

                last_line.append(token.value)
            else:
                # Last iteration
                doc.extend(last_line)

        if doc:
            # Case with multiple Setting sections
            break

    ret = "".join(doc).strip()
    return ret


def get_documentation_as_markdown(ast) -> str:
    documentation = get_documentation_raw(ast)
    if not documentation:
        return documentation
    try:
        from robotframework_ls import robot_to_markdown

        return robot_to_markdown.convert(documentation)
    except:
        log.exception("Error converting to markdown: %s", documentation)
        return documentation


@_convert_ast_to_indexer
def iter_local_assigns(ast) -> Iterator:
    from robot.api import Token

    for clsname, assign_token_type in (
        ("KeywordCall", Token.ASSIGN),
        ("ForHeader", Token.VARIABLE),
        ("ExceptHeader", Token.VARIABLE),
        ("InlineIfHeader", Token.ASSIGN),
    ):
        for node_info in ast.iter_indexed(clsname):
            node = node_info.node
            for token in node.tokens:
                if token.type == assign_token_type:
                    value = token.value

                    i = value.find("{")
                    j = value.rfind("}")
                    if i != -1 and j != -1 and i >= 1:
                        new_value = value[i + 1 : j]
                        token = Token(
                            type=token.type,
                            value=new_value,
                            lineno=token.lineno,
                            col_offset=token.col_offset + i + 1,
                            error=token.error,
                        )

                        yield VarTokenInfo(node_info.stack, node, token, value[0])


_FIXTURE_CLASS_NAMES = (
    "Setup",
    "Teardown",
    "SuiteSetup",
    "SuiteTeardown",
    "TestSetup",
    "TestTeardown",
)

_CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE = _FIXTURE_CLASS_NAMES + (
    "TestTemplate",
    "Template",
)

CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET = frozenset(
    _CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE
)

CLASSES_WTH_EXPRESSION_ARGUMENTS = ("IfHeader", "ElseIfHeader", "WhileHeader")


def _tokenize_subvars(initial_token: IRobotToken) -> Iterator[Tuple[IRobotToken, str]]:
    from robot.api import Token

    if "{" not in initial_token.value:
        return

    if initial_token.value.startswith("{") and initial_token.value.endswith("}"):
        # i.e.: We're dealing with an expression.
        _first, second, _third = split_token_in_3(
            initial_token,
            "variableOperator",
            "argumentValue",
            "variableOperator",
            1,
            -1,
        )

        for tok in iter_expression_variables(second):
            yield tok, "$"
        return

    skip_type = ""
    robot_match_generator = RobotMatchTokensGenerator(initial_token, skip_type)
    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches

    for robot_match, relative_index in iter_robot_variable_matches(initial_token.value):
        for token in robot_match_generator.gen_tokens_from_robot_match(
            robot_match, relative_index, skip_type, initial_token.type
        ):
            if token.type == initial_token.type:
                found = False
                for v in _tokenize_subvars(token):
                    found = True
                    yield v

                if not found:
                    yield token, robot_match.identifier


@_convert_ast_to_indexer
def iter_variable_references(ast) -> Iterator[VarTokenInfo]:
    # TODO: This right now makes everything globally, we should have 2 versions,
    # one to resolve references which are global and another to resolve references
    # just inside some scope when dealing with local variables.
    # Right now we're not very smart and even if a variable is local we'll reference
    # global variables...

    # Note: we collect only the references, not the definitions here!
    for clsname in (
        "KeywordCall",
        "LibraryImport",
        "ResourceImport",
        "TestTimeout",
        "Variable",
        "ForHeader",
    ) + _CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE:
        for node_info in ast.iter_indexed(clsname):
            stack = node_info.stack
            node = node_info.node
            token = None
            try:
                for token in node.tokens:
                    if token.type in (token.ARGUMENT, token.NAME):
                        for tok in tokenize_variables(token):
                            if tok.type == token.VARIABLE:

                                # We need to check for inner variables (as in
                                # this case we validate those).
                                for t, var_identifier in _tokenize_subvars(tok):
                                    yield VarTokenInfo(stack, node, t, var_identifier)

            except:
                log.exception("Unable to tokenize: %s", token)

    for clsname in CLASSES_WTH_EXPRESSION_ARGUMENTS:
        for node_info in ast.iter_indexed(clsname):
            stack = node_info.stack
            node = node_info.node
            token = None

            try:
                for token in node.tokens:
                    if token.type == token.ARGUMENT:
                        for tok in iter_expression_variables(token):
                            if tok.type == token.VARIABLE:
                                yield VarTokenInfo(stack, node, tok, "$")
            except:
                log.exception("Unable to tokenize: %s", token)

    for node_info in ast.iter_indexed("Keyword"):
        for token in _iter_keyword_arguments_tokens(
            node_info.node, tokenize_keyword_name=True
        ):
            iter_in = _tokenize_subvars(token)

            try:
                # The first one is the variable store (the other is the
                # variable load on a default argument)
                # We are only interested in the second in this API.
                next(iter_in)
            except StopIteration:
                continue

            for t, varid in iter_in:
                yield VarTokenInfo(stack, node, t, varid)


@_convert_ast_to_indexer
def iter_keyword_usage_tokens(
    ast, collect_args_as_keywords: bool
) -> Iterator[KeywordUsageInfo]:
    """
    Iterates through all the places where a keyword name is being used, providing
    the stack, node, token and name.
    """

    cache_key = ("iter_keyword_usage_tokens", collect_args_as_keywords)
    yield from ast.iter_cached(
        cache_key, _iter_keyword_usage_tokens_uncached, collect_args_as_keywords
    )


def _same_line_col(tok1: IRobotToken, tok2: IRobotToken):
    return tok1.lineno == tok2.lineno and tok1.col_offset == tok2.col_offset


def _build_keyword_usage(
    stack, node, yield_only_for_token, current_tokens, found_at_index
) -> Optional[KeywordUsageInfo]:
    # Note: just check for line/col because the token could be changed
    # (for instance, an EOL ' ' could be added to the token).

    if yield_only_for_token is None or _same_line_col(
        yield_only_for_token, current_tokens[found_at_index]
    ):
        current_token = current_tokens[found_at_index]
        current_token = copy_token_replacing(current_token, type=current_token.KEYWORD)
        new_tokens = [current_token]
        new_tokens.extend(current_tokens[found_at_index + 1 :])

        return KeywordUsageInfo(
            stack,
            node.__class__(new_tokens),
            current_token,
            current_token.value,
            True,
        )
    return None


def _iter_keyword_usage_tokens_uncached_from_args(
    stack, node, args_as_keywords_handler, yield_only_for_token=None
):
    # We may have multiple matches, so, we need to setup the appropriate book-keeping
    current_tokens = []
    found_at_index = -1

    for token in node.tokens:
        if token.type == token.ARGUMENT:
            current_tokens.append(token)
            if args_as_keywords_handler.consider_current_argument_token_as_keyword(
                token
            ):
                found_at_index = len(current_tokens) - 1
            else:
                if args_as_keywords_handler.started_match:
                    del current_tokens[-1]  # Don't add the ELSE IF/ELSE argument.
                    usage_info = _build_keyword_usage(
                        stack,
                        node,
                        yield_only_for_token,
                        current_tokens,
                        found_at_index,
                    )
                    if usage_info is not None:
                        yield usage_info
                    current_tokens = []
                    found_at_index = -1
    else:
        # Do one last iteration at the end to deal with the last one.
        if found_at_index >= 0 and len(current_tokens) > found_at_index:
            usage_info = _build_keyword_usage(
                stack, node, yield_only_for_token, current_tokens, found_at_index
            )
            if usage_info is not None:
                yield usage_info


def _iter_keyword_usage_tokens_uncached(ast, collect_args_as_keywords):
    for clsname in ("KeywordCall",) + _CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE:
        for node_info in ast.iter_indexed(clsname):
            stack = node_info.stack
            node = node_info.node
            usage_info = _create_keyword_usage_info(stack, node)
            if usage_info is not None:
                yield usage_info

                if collect_args_as_keywords:
                    args_as_keywords_handler = get_args_as_keywords_handler(
                        usage_info.node
                    )
                    if args_as_keywords_handler is None:
                        continue

                    yield from _iter_keyword_usage_tokens_uncached_from_args(
                        stack, node, args_as_keywords_handler
                    )


def _create_keyword_usage_info(stack, node) -> Optional[KeywordUsageInfo]:
    """
    If this is a keyword usage node, return information on it, otherwise,
    returns None.

    :note: this goes hand-in-hand with get_keyword_name_token.
    """
    from robot.api import Token

    if node.__class__.__name__ == "KeywordCall":
        token_type = Token.KEYWORD

    elif node.__class__.__name__ in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET:
        token_type = Token.NAME

    else:
        return None

    node, token = _strip_node_and_token_bdd_prefix(node, token_type)
    if token is None:
        return None

    keyword_name = token.value
    if keyword_name.lower() == "none":
        return None
    return KeywordUsageInfo(tuple(stack), node, token, keyword_name)


def create_keyword_usage_info_from_token(
    stack: Tuple[INode, ...], node: INode, token: IRobotToken
) -> Optional[KeywordUsageInfo]:
    """
    If this is a keyword usage node, return information on it, otherwise,
    returns None.

    Note that it should return the keyword usage for the whole keyword call
    if we're in an argument that isn't itself a keyword call.
    """
    if token.type == token.ARGUMENT:
        args_as_keywords_handler = get_args_as_keywords_handler(node)
        if args_as_keywords_handler is not None:
            for v in _iter_keyword_usage_tokens_uncached_from_args(
                stack,
                node,
                args_as_keywords_handler,
                yield_only_for_token=token,
            ):
                return v

    return _create_keyword_usage_info(stack, node)


class _ConsiderArgsAsKeywordNames:
    def __init__(
        self,
        normalized_keyword_name,
        consider_keyword_at_index,
        consider_condition_at_index,
    ):
        self._normalized_keyword_name = normalized_keyword_name
        self._consider_keyword_at_index = consider_keyword_at_index
        self._consider_condition_at_index = consider_condition_at_index
        self._current_arg = 0

        # Run Keyword If is special because it has 'ELSE IF' / 'ELSE'
        # which will then be be (cond, keyword) or just (keyword), so
        # we need to provide keyword usages as needed.
        self.multiple_matches = self._normalized_keyword_name == "runkeywordif"

        self._stack_kind = None
        self._stack = None
        self.started_match = False
        self.was_last_expression_argument = False

    def consider_current_argument_token_as_keyword(self, token) -> bool:
        assert token.type == token.ARGUMENT

        self._current_arg += 1

        if self.multiple_matches:
            if token.value == "ELSE IF":
                self.started_match = True
                self._stack = []
                self._stack_kind = token.value
            elif token.value == "ELSE":
                self.started_match = True
                self._stack = []
                self._stack_kind = token.value

            else:
                self.started_match = False
                if self._stack is not None:
                    self._stack.append(token)

            if self._stack is not None:
                if self._stack_kind == "ELSE IF":
                    self.was_last_expression_argument = len(self._stack) == 1
                    return len(self._stack) == 2

                if self._stack_kind == "ELSE":
                    self.was_last_expression_argument = False
                    return len(self._stack) == 1

        self.was_last_expression_argument = (
            self._current_arg == self._consider_condition_at_index
        )
        return self._current_arg == self._consider_keyword_at_index


def get_args_as_keywords_handler(node) -> Optional[_ConsiderArgsAsKeywordNames]:
    if isinstance_name(node, "KeywordCall"):
        node_keyword_name = node.keyword
        if node_keyword_name:
            normalized_keyword_name = normalize_robot_name(node_keyword_name)
            consider_keyword_at_index = KEYWORD_NAME_TO_KEYWORD_INDEX.get(
                normalized_keyword_name
            )
            consider_condition_at_index = KEYWORD_NAME_TO_CONDITION_INDEX.get(
                normalized_keyword_name
            )
            if (
                consider_keyword_at_index is not None
                or consider_condition_at_index is not None
            ):
                return _ConsiderArgsAsKeywordNames(
                    normalized_keyword_name,
                    consider_keyword_at_index,
                    consider_condition_at_index,
                )
    return None


def get_keyword_name_token(
    stack: Tuple[INode, ...], node: INode, token: IRobotToken
) -> Optional[IRobotToken]:
    """
    If the given token is a keyword call name, return the token, otherwise return None.

    :note: this goes hand-in-hand with iter_keyword_usage_tokens.
    """
    if token.type == token.KEYWORD or (
        token.type == token.NAME
        and node.__class__.__name__ in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET
    ):
        return _strip_token_bdd_prefix(token)

    if token.type == token.ARGUMENT and not token.value.strip().endswith("}"):
        args_as_keywords_handler = get_args_as_keywords_handler(node)
        if args_as_keywords_handler is not None:
            for _ in _iter_keyword_usage_tokens_uncached_from_args(
                stack,
                node,
                args_as_keywords_handler,
                yield_only_for_token=token,
            ):
                return token
    return None


def get_library_import_name_token(node, token: IRobotToken) -> Optional[IRobotToken]:
    """
    If the given ast node is a library import and the token is its name, return
    the name token, otherwise, return None.
    """

    if (
        token.type == token.NAME
        and isinstance_name(node, "LibraryImport")
        and node.name == token.value  # I.e.: match the name, not the alias.
    ):
        return token
    return None


def get_resource_import_name_token(node, token: IRobotToken) -> Optional[IRobotToken]:
    """
    If the given ast node is a library import and the token is its name, return
    the name token, otherwise, return None.
    """

    if (
        token.type == token.NAME
        and isinstance_name(node, "ResourceImport")
        and node.name == token.value  # I.e.: match the name, not the alias.
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


def copy_token_replacing(token, **kwargs):
    from robot.api import Token

    new_kwargs = {
        "type": token.type,
        "value": token.value,
        "lineno": token.lineno,
        "col_offset": token.col_offset,
        "error": token.error,
    }
    new_kwargs.update(kwargs)
    return Token(**new_kwargs)


def copy_token_with_subpart(token, start, end):
    from robot.api import Token

    return Token(
        type=token.type,
        value=token.value[start:end],
        lineno=token.lineno,
        col_offset=token.col_offset + start,
        error=token.error,
    )


def create_range_from_token(token) -> RangeTypedDict:

    start: PositionTypedDict = {"line": token.lineno - 1, "character": token.col_offset}
    end: PositionTypedDict = {
        "line": token.lineno - 1,
        "character": token.end_col_offset,
    }
    code_lens_range: RangeTypedDict = {"start": start, "end": end}
    return code_lens_range


def create_token(name):
    from robot.api import Token

    return Token(Token.NAME, name)


def convert_variable_match_base_to_token(
    token: IRobotToken, variable_match: IRobotVariableMatch
):
    from robot.api import Token

    base = variable_match.base
    assert base is not None
    s = variable_match.string
    if not base:
        base_i = s.find("{") + 1
    else:
        base_i = s.find(base)

    return Token(
        type=token.type,
        value=variable_match.base,
        lineno=token.lineno,
        col_offset=token.col_offset + variable_match.start + base_i,
        error=token.error,
    )


def iter_robot_match_as_tokens(
    robot_match: IRobotVariableMatch, relative_index: int = 0, lineno: int = 0
) -> Iterator[IRobotToken]:
    from robot.api import Token

    base = robot_match.base
    assert base is not None
    s = robot_match.string
    if not base:
        base_i = s.find("{") + 1
    else:
        base_i = s.find(base)

    yield Token(
        type="base",
        value=base,
        lineno=lineno,
        col_offset=relative_index + robot_match.start + base_i,
    )

    last_i = base_i + len(base)
    for item in robot_match.items:
        open_char_i = s.find("[", last_i)
        if open_char_i > 0:
            yield Token(
                type="[",
                value="[",
                lineno=lineno,
                col_offset=relative_index + robot_match.start + open_char_i,
            )

            last_i = open_char_i + 1

        if not item:
            item_i = last_i
        else:
            item_i = s.find(item, last_i)

        yield Token(
            type="item",
            value=item,
            lineno=lineno,
            col_offset=relative_index + robot_match.start + item_i,
        )

        last_i = item_i + len(item)

        close_char_i = s.find("]", last_i)
        if close_char_i < 0:
            break

        yield Token(
            type="]",
            value="]",
            lineno=lineno,
            col_offset=relative_index + robot_match.start + close_char_i,
        )

        last_i = close_char_i


def split_token_in_3(
    token: IRobotToken,
    first_token_type: str,
    second_token_type: str,
    third_token_type,
    start_pos,
    end_pos,
) -> Tuple[IRobotToken, IRobotToken, IRobotToken]:
    first = copy_token_replacing(
        token,
        type=first_token_type,
        value=token.value[:start_pos],
    )
    second = copy_token_replacing(
        token,
        type=second_token_type,
        value=token.value[start_pos:end_pos],
        col_offset=token.col_offset + start_pos,
    )

    if end_pos < 0:
        third = copy_token_replacing(
            token,
            type=third_token_type,
            value=token.value[:end_pos],
            col_offset=second.end_col_offset,
        )
    else:
        third = copy_token_replacing(
            token,
            type=third_token_type,
            value=token.value[end_pos:],
            col_offset=second.end_col_offset,
        )

    return first, second, third


def split_token_change_first(
    token: IRobotToken, first_token_type: str, position: int
) -> Tuple[IRobotToken, IRobotToken]:
    prefix = copy_token_replacing(
        token,
        type=first_token_type,
        value=token.value[:position],
    )
    remainder = copy_token_replacing(
        token, value=token.value[position:], col_offset=prefix.end_col_offset
    )
    return prefix, remainder


def split_token_change_second(
    token: IRobotToken, second_token_type: str, position: int
) -> Tuple[IRobotToken, IRobotToken]:
    prefix = copy_token_replacing(
        token,
        value=token.value[:position],
    )
    remainder = copy_token_replacing(
        token,
        value=token.value[position:],
        col_offset=prefix.end_col_offset,
        type=second_token_type,
    )
    return prefix, remainder


def get_library_arguments_serialized(library) -> Optional[str]:
    return "::".join(library.args) if library.args else None


def iter_expression_variables(expression_token: IRobotToken) -> Iterator[IRobotToken]:
    from robot.api import Token

    for tok in iter_expression_tokens(expression_token):
        if tok.type == "variable":
            yield copy_token_replacing(tok, type=Token.VARIABLE)


class RobotMatchTokensGenerator:
    def __init__(self, token, default_type):
        self.default_type = default_type
        self.token = token
        self.last_gen_end_offset = 0

    def gen_default_type(self, until_offset: int) -> Iterable[IRobotToken]:
        token = self.token
        if until_offset > self.last_gen_end_offset:
            from robot.api import Token

            val = token.value[self.last_gen_end_offset : until_offset]
            if val.strip():  # Don't generate just for whitespaces.
                yield Token(
                    self.default_type,
                    val,
                    token.lineno,
                    token.col_offset + self.last_gen_end_offset,
                    token.error,
                )

    def gen_tokens_from_robot_match(
        self,
        robot_match: IRobotVariableMatch,
        last_relative_index: int,
        op_type: str = "variableOperator",
        var_type: str = "variable",
    ) -> Iterable[IRobotToken]:
        from robot.api import Token

        token = self.token
        if not robot_match.base:
            i = token.value.find("{", robot_match.start + last_relative_index) + 1
        else:
            i = token.value.find(
                robot_match.base, robot_match.start + last_relative_index
            )

        start_offset = robot_match.start + last_relative_index

        yield from self.gen_default_type(start_offset)

        yield Token(
            op_type,
            token.value[robot_match.start + last_relative_index : i],
            token.lineno,
            token.col_offset + start_offset,
            token.error,
        )

        yield Token(
            var_type,
            robot_match.base,
            token.lineno,
            token.col_offset + i,
            token.error,
        )

        base = robot_match.base
        assert base is not None
        j = i + len(base)

        val = token.value[j : robot_match.end + last_relative_index]
        yield Token(
            op_type,
            val,
            token.lineno,
            token.col_offset + j,
            token.error,
        )

        self.last_gen_end_offset = j + len(val)


def iter_expression_tokens(
    expression_token: IRobotToken, default_type="argument"
) -> Iterator[IRobotToken]:
    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches
    from tokenize import generate_tokens, NAME, ERRORTOKEN
    from io import StringIO
    from robot.api import Token

    robot_match_generator = RobotMatchTokensGenerator(expression_token, default_type)

    # Note: tokens yielded are tokens which are internal LS types (not RF types).
    # Use: iter_expression_variables to get the vars with RF types.

    # See: robot.variables.evaluation.evaluate_expression

    iter_robot_match = iter_robot_variable_matches(expression_token.value)
    last_robot_match = None

    try:
        last_robot_match, last_relative_index = next(iter_robot_match)
    except StopIteration:
        pass

    gen_var_token_info: Any = None
    for token_info in generate_tokens(StringIO(expression_token.value).readline):
        if token_info.type == ERRORTOKEN and token_info.string == "$":
            gen_var_token_info = token_info

        elif gen_var_token_info is not None and token_info.type == NAME:
            if gen_var_token_info.start[1] == token_info.start[1] - 1:

                while True:
                    if last_robot_match is None or last_robot_match.base is None:
                        break

                    if (
                        last_robot_match.start + last_relative_index
                        < gen_var_token_info.start[1]
                    ):
                        yield from robot_match_generator.gen_tokens_from_robot_match(
                            last_robot_match, last_relative_index
                        )

                        last_robot_match = None

                        try:
                            last_robot_match, last_relative_index = next(
                                iter_robot_match
                            )
                        except StopIteration:
                            pass
                    else:
                        break

                start_offset = gen_var_token_info.start[1]
                yield from robot_match_generator.gen_default_type(start_offset)

                yield Token(
                    "variableOperator",
                    gen_var_token_info.string,
                    expression_token.lineno,
                    expression_token.col_offset + start_offset,
                    expression_token.error,
                )

                yield Token(
                    "variable",
                    token_info.string,
                    expression_token.lineno,
                    expression_token.col_offset + token_info.start[1],
                    expression_token.error,
                )

                robot_match_generator.last_gen_end_offset = token_info.start[1] + len(
                    token_info.string
                )

            gen_var_token_info = None

    while True:
        if last_robot_match is None or last_robot_match.base is None:
            break

        yield from robot_match_generator.gen_tokens_from_robot_match(
            last_robot_match, last_relative_index
        )

        last_robot_match = None

        try:
            last_robot_match, last_relative_index = next(iter_robot_match)
        except StopIteration:
            pass

    yield from robot_match_generator.gen_default_type(len(expression_token.value))


def is_node_with_expression_argument(node):
    if node.__class__.__name__ == "KeywordCall":
        kw_name = node.keyword
        return kw_name and normalize_robot_name(kw_name) == "evaluate"
    else:
        return node.__class__.__name__ in CLASSES_WTH_EXPRESSION_ARGUMENTS
