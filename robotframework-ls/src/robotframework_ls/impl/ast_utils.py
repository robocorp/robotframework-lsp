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
    Sequence,
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
    VariableKind,
    AdditionalVarInfo,
)
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robocorp_ls_core.basic import isinstance_name
import functools
import weakref
import threading
import typing
import itertools
from robotframework_ls.impl.robot_localization import LocalizationInfo
from functools import lru_cache


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


@lru_cache(None)
def _get_error_tokens():
    from robot.api import Token

    ret = [Token.ERROR, Token.FATAL_ERROR]
    try:
        # Only available in 6.1 onwards.
        ret.append(Token.INVALID_HEADER)
    except AttributeError:
        pass
    return tuple(ret)


def _get_errors_from_tokens(node):
    error_tokens = _get_error_tokens()
    for token in node.tokens:
        if token.type in error_tokens:
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
        if hasattr(ast, "iter_indexed"):
            indexer = ast
        else:
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
        elif node.__class__.__name__ == "InvalidSection":
            # On 6.1 we don't have an Error in this case, we have a regular class
            # named "InvalidSection".
            errors.extend(_get_errors_from_tokens(node.header))

        elif use_errors_attribute:
            node_errors = getattr(node, "errors", ())
            if node_errors:
                for error in node_errors:
                    errors.append(create_error_from_node(node, error, tokens=[node]))

        if len(errors) >= MAX_ERRORS:
            break

    return errors


def create_error_from_node(node, msg, tokens=None, **kwargs) -> Error:
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

    error = Error(msg, start, end, **kwargs)
    return error


def print_ast(node, stream=None):
    if stream is None:
        stream = sys.stderr
    errors_visitor = _PrinterVisitor(stream)
    errors_visitor.visit(node)


def iter_sections(node):
    yield from iter(node.sections)


def find_keyword_section(node):
    for section in iter_sections(node):
        if isinstance_name(section, "KeywordSection"):
            return section
    return None


def find_variable_section(node):
    for section in iter_sections(node):
        if isinstance_name(section, "VariableSection"):
            return section
    return None


def is_keyword_section(node) -> bool:
    return isinstance_name(node, "KeywordSection")


def is_testcase_section(node) -> bool:
    return isinstance_name(node, "TestCaseSection")


def find_section(node, line: int) -> Optional[INode]:
    """
    :param line:
        0-based
    """
    last_section = None
    for section in iter_sections(node):
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


def get_local_variable_stack_and_node(
    stack: Sequence[INode],
) -> Tuple[Tuple[INode, ...], INode]:
    """
    Provides the stack to search local variables in (i.e.: the keyword/test case).

    Note that this requires a valid stack.
    """
    assert stack, "This method requires a valid stack."

    stack_lst: List[INode] = []
    for local_stack_node in reversed(stack):
        stack_lst.append(local_stack_node)
        if local_stack_node.__class__.__name__ in ("Keyword", "TestCase"):
            stack = tuple(stack_lst)
            break
    else:
        stack = (local_stack_node,)
        local_stack_node = stack[0]
    return stack, local_stack_node


def matches_stack(
    def_stack: Optional[Sequence[INode]], stack: Optional[Sequence[INode]]
) -> bool:
    """
    Note: just checks the stack, the source must be already validated at this point.
    """
    if stack is not None:
        if def_stack is None:
            return False

        if stack:
            if not def_stack:
                return False

            if stack[-1].lineno == def_stack[-1].lineno:
                return True

            # Not directly the same (we could be inside some for/while, so, let's
            # see if we can get the keyword/testcase from the stack).
            _, node1 = get_local_variable_stack_and_node(stack)
            _, node2 = get_local_variable_stack_and_node(def_stack)
            return node1.lineno == node2.lineno

    return True


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
        if node.__class__.__name__ != "File":
            stack.append(node)
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


def _iter_nodes_reverse(node) -> Iterator[INode]:
    """
    Iterate over nodes in reverse order.
    """
    for field in reversed(node._fields):
        try:
            value = getattr(node, field)
        except AttributeError:
            continue

        if isinstance(value, list):
            for item in reversed(value):
                if isinstance(item, _AST_CLASS):
                    # i.e.: First go into
                    yield from _iter_nodes_reverse(item)
                    # And the provide current
                    yield item

        elif isinstance(value, _AST_CLASS):
            yield from _iter_nodes_reverse(value)


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
    for token, var_info in _tokenize_subvars(initial_token):
        if token.type == token.ARGUMENT:
            continue

        if token.col_offset <= col <= token.end_col_offset:
            if initial_token.type == initial_token.ASSIGN:
                token = copy_token_replacing(token, type=initial_token.ASSIGN)
            return VarTokenInfo(stack, node, token, var_info)

    from robotframework_ls.impl import robot_constants

    for p in robot_constants.VARIABLE_PREFIXES:
        if initial_token.value.startswith(p + "{"):
            if (
                initial_token.type == initial_token.ASSIGN
                and initial_token.value.endswith("}=")
            ):
                var_token = copy_token_with_subpart(initial_token, 2, -2)
            elif initial_token.value.endswith("}"):
                var_token = copy_token_with_subpart(initial_token, 2, -1)
            else:
                var_token = copy_token_with_subpart(
                    initial_token, 2, len(initial_token.value)
                )

            var_info = AdditionalVarInfo(p)
            return VarTokenInfo(stack, node, var_token, var_info)
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
            if token.type == token.ARGUMENT and is_node_with_expression_argument(node):
                for part, var_info in iter_expression_variables(token):
                    if part.type == token.VARIABLE:
                        if part.col_offset <= col <= part.end_col_offset:
                            return VarTokenInfo(
                                stack,
                                node,
                                part,
                                var_info.copy(
                                    context=AdditionalVarInfo.CONTEXT_EXPRESSION
                                ),
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
                                AdditionalVarInfo(
                                    "$",
                                    AdditionalVarInfo.CONTEXT_EXPRESSION,
                                ),
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


def tokenize_variables(token: IRobotToken) -> Iterator[IRobotToken]:
    # May throw error if it's not OK.
    return iter(tuple(token.tokenize_variables()))


def _tokenize_variables_even_when_invalid(
    token: IRobotToken, col: int
) -> Iterator[IRobotToken]:
    """
    If Token.tokenize_variables() fails, this can still provide the variable under
    the given column by applying some heuristics to find open variables.
    """
    try:
        return iter(tuple(tokenize_variables(token)))
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

            return iter(
                [
                    Token(
                        type=token.VARIABLE,
                        value="".join(varname),
                        lineno=token.lineno,
                        col_offset=token.col_offset + open_at - 1,
                        error=token.error,
                    )
                ]
            )
    return iter(())


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
    cache_key = "iter_library_imports"
    yield from ast.iter_cached(cache_key, _iter_library_imports_uncached)


def _iter_library_imports_uncached(ast):
    try:
        from robot.api.parsing import LibraryImport  # noqa
    except ImportError:
        from robot.parsing.model.statements import LibraryImport  # noqa

    yield from ast.iter_indexed("LibraryImport")
    for keyword_usage_info in iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        if normalize_robot_name(keyword_usage_info.name) == "importlibrary":
            # Create a LibraryImport node based on the keyword usage.
            use_tokens = []
            iter_in = iter(keyword_usage_info.node.tokens)
            for token in iter_in:
                if token.type == token.KEYWORD:
                    # Skip the 'Import Library' keyword name.
                    break
            else:
                continue

            # Get the first non-separator token
            for token in iter_in:
                if token.type == token.SEPARATOR:
                    continue
                use_tokens.append(copy_token_replacing(token, type=token.NAME))
                break

            for token in iter_in:
                if token.type == token.ARGUMENT and token.value == "WITH NAME":
                    use_tokens.append(copy_token_replacing(token, type=token.WITH_NAME))
                    for token in iter_in:
                        if token.type == token.ARGUMENT:
                            use_tokens.append(
                                copy_token_replacing(token, type=token.NAME)
                            )
                        else:
                            use_tokens.append(token)

                else:
                    use_tokens.append(token)

            if use_tokens:
                node = LibraryImport(use_tokens)
                yield NodeInfo(keyword_usage_info.stack, node)


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
) -> Iterator[IRobotToken]:
    """
    This API provides tokens as they are.

    i.e.: it returns tokens as: ${my.store}=${my.load}[first][second]

    So, this is internal as the outer world is tailored to
    dealing with what's actually needed.

    Note that it may return Token.ARGUMENT types (if defined in [Argument]) or
    Token.VARIABLE (if defined in keyword name).
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


def iter_keyword_arguments_as_tokens(ast) -> Iterator[IRobotToken]:
    """
    API tailored at getting variables from keyword arguments.

    It converts an argument such as:
    "[Arguments]    ${my.store}=${my.load}[first][second]"

    and yields something as:

    "my.store"

    It may also convert keyword arguments in the keyword name such as:

    "Today is ${date:\d{4}-\d{2}-\d{2}}"

    to "date"
    """
    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches
    from robot.api import Token

    for initial_token in _iter_keyword_arguments_tokens(
        ast, tokenize_keyword_name=True
    ):
        for robot_match, _relative_index in iter_robot_variable_matches(
            initial_token.value
        ):
            i = initial_token.value.find(robot_match.base, robot_match.start)

            t = Token(
                initial_token.type,
                robot_match.base,
                initial_token.lineno,
                initial_token.col_offset + i,
                initial_token.error,
            )
            if initial_token.type == initial_token.VARIABLE:
                i = t.value.find(":")
                if i > 0:
                    t = copy_token_with_subpart(t, 0, i)
            yield t
            break  # Go to next arg.


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


KEYWORD_SET_LOCAL_TO_VAR_KIND = {
    normalize_robot_name("Set Local Variable"): VariableKind.LOCAL_SET_VARIABLE,
}

KEYWORD_SET_GLOBAL_TO_VAR_KIND = {
    normalize_robot_name("Set Task Variable"): VariableKind.TASK_SET_VARIABLE,
    normalize_robot_name("Set Test Variable"): VariableKind.TEST_SET_VARIABLE,
    normalize_robot_name("Set Suite Variable"): VariableKind.SUITE_SET_VARIABLE,
    normalize_robot_name("Set Global Variable"): VariableKind.GLOBAL_SET_VARIABLE,
}


KEYWORD_SET_ENV_TO_VAR_KIND = {
    normalize_robot_name("Set Environment Variable"): VariableKind.ENV_SET_VARIABLE,
}


@_convert_ast_to_indexer
def iter_local_assigns(ast) -> Iterator[VarTokenInfo]:
    from robot.api import Token

    for clsname, assign_token_type in (
        ("KeywordCall", Token.ASSIGN),
        ("ForHeader", Token.VARIABLE),  # RF 4+
        ("ForHeader", Token.ASSIGN),  # RF > 6.1
        ("ForLoopHeader", Token.VARIABLE),  # RF 3
        ("ExceptHeader", Token.VARIABLE),  # RF <= 6.1
        ("ExceptHeader", Token.ASSIGN),  # RF > 6.1
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

_CLASSES_KEYWORDS_AND_OTHERS_WITH_ARGUMENTS_AS_KEYWORD_CALLS = (
    "KeywordCall",
) + _CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE

CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET = frozenset(
    _CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_TUPLE
)

CLASSES_WTH_EXPRESSION_ARGUMENTS = (
    "IfHeader",
    "ElseIfHeader",
    "WhileHeader",
    "InlineIfHeader",
)


def _tokenize_subvars(
    initial_token: IRobotToken,
) -> Iterator[Tuple[IRobotToken, AdditionalVarInfo]]:
    if "{" not in initial_token.value:
        return

    for tok, var_info in _tokenize_subvars_tokens(initial_token):
        if tok.type in (tok.ARGUMENT, tok.VARIABLE):
            yield tok, var_info


def _tokenize_subvars_tokens(
    initial_token: IRobotToken,
    op_type: str = "variableOperator",
    var_type: Optional[str] = None,
) -> Iterator[Tuple[IRobotToken, AdditionalVarInfo]]:
    from robot.api import Token

    if var_type is None:
        var_type = Token.ARGUMENT

    if "{" not in initial_token.value:
        return

    if initial_token.value.startswith("{") and initial_token.value.endswith("}"):
        # i.e.: We're dealing with an expression.
        first, second, third = split_token_in_3(
            initial_token,
            op_type,
            var_type,
            op_type,
            1,
            -1,
        )
        yield first, AdditionalVarInfo()
        yield from iter_expression_tokens(second)
        yield third, AdditionalVarInfo()
        return

    robot_match_generator = RobotMatchTokensGenerator(initial_token, var_type)
    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches

    for robot_match, relative_index in iter_robot_variable_matches(initial_token.value):
        yield from robot_match_generator.gen_default_type(
            relative_index + len(robot_match.before)
        )

        yield from robot_match_generator.gen_tokens_from_robot_match(
            robot_match, relative_index, var_type=var_type
        )

    yield from robot_match_generator.gen_default_type(len(initial_token.value))


def _is_store_keyword(node):
    from robot.api import Token

    keyword_name_tok = node.get_token(Token.KEYWORD)
    if not keyword_name_tok:
        return False
    normalized = normalize_robot_name(keyword_name_tok.value)
    return (
        normalized in KEYWORD_SET_LOCAL_TO_VAR_KIND
        or normalized in KEYWORD_SET_GLOBAL_TO_VAR_KIND
    )


def _add_match(found: set, tok: IRobotToken) -> bool:
    """
    Helper to avoid returning 2 matches in the same position if 2 different
    heuristics overlap what they can return.
    """
    key = tok.col_offset, tok.lineno
    if key in found:
        return False
    found.add(key)
    return True


@_convert_ast_to_indexer
def iter_variable_references(ast) -> Iterator[VarTokenInfo]:
    from robotframework_ls.impl.ast_utils_keyword_usage import (
        obtain_keyword_usage_handler,
    )

    # TODO: This right now makes everything globally, we should have 2 versions,
    # one to resolve references which are global and another to resolve references
    # just inside some scope when dealing with local variables.
    # Right now we're not very smart and even if a variable is local we'll reference
    # global variables...

    # Note: we collect only the references, not the definitions here!
    found: set = set()
    for clsname in (
        "KeywordCall",
        "LibraryImport",
        "ResourceImport",
        "TestTimeout",
        "Variable",
        "ForHeader",  # RF 4+
        "ForLoopHeader",  # RF 3
        "ReturnStatement",  # RF 5
    ) + _FIXTURE_CLASS_NAMES:
        for node_info in ast.iter_indexed(clsname):
            stack = node_info.stack
            node = node_info.node
            token = None
            arg_i = 0
            for token in node.tokens:
                try:
                    if token.type == token.ARGUMENT:
                        arg_i += 1
                        if arg_i == 1 and clsname == "KeywordCall":
                            if _is_store_keyword(node_info.node):
                                continue

                    if token.type == token.KEYWORD:
                        # Keyword calls may also have variables (unfortunately
                        # RF doesn't tokenize it with that type, so, we have
                        # to apply a workaround to change the type).
                        token = copy_token_replacing(token, type=token.NAME)

                    if token.type in (token.ARGUMENT, token.NAME):
                        for tok in tokenize_variables(token):
                            if tok.type == token.VARIABLE:
                                # We need to check for inner variables (as in
                                # this case we validate those).
                                for t, var_info in _tokenize_subvars(tok):
                                    if t.type != token.VARIABLE:
                                        continue
                                    if not _add_match(found, t):
                                        continue

                                    yield VarTokenInfo(stack, node, t, var_info)

                except:
                    log.exception("Unable to tokenize: %s", token)

    for node_info in _iter_node_info_which_may_have_usage_info(ast):
        stack = node_info.stack
        node = node_info.node
        keyword_usage_handler = obtain_keyword_usage_handler(stack, node)
        if keyword_usage_handler is not None:
            for usage_info in keyword_usage_handler.iter_keyword_usages_from_node():
                arg_i = 0
                for token in usage_info.node.tokens:
                    if token.type == token.ARGUMENT:
                        arg_i += 1
                        if arg_i == 1:
                            if _is_store_keyword(usage_info.node):
                                continue

                        next_tok_type = keyword_usage_handler.get_token_type(token)
                        if next_tok_type == keyword_usage_handler.EXPRESSION:
                            for tok, var_info in iter_expression_variables(token):
                                if tok.type == token.VARIABLE:
                                    if not _add_match(found, tok):
                                        continue
                                    yield VarTokenInfo(stack, node, tok, var_info)

    for clsname in CLASSES_WTH_EXPRESSION_ARGUMENTS:
        for node_info in ast.iter_indexed(clsname):
            stack = node_info.stack
            node = node_info.node
            token = None

            for token in node.tokens:
                try:
                    if token.type == token.ARGUMENT:
                        for tok, var_info in iter_expression_variables(token):
                            if tok.type == token.VARIABLE:
                                if not _add_match(found, tok):
                                    continue
                                yield VarTokenInfo(stack, node, tok, var_info)
                except:
                    log.exception("Unable to tokenize: %s", token)

    iter_keyword_node_info: Iterator[NodeInfo]
    if isinstance_name(ast.ast, "Keyword"):
        iter_keyword_node_info = iter((NodeInfo((ast.ast,), ast.ast),))
    else:
        iter_keyword_node_info = ast.iter_indexed("Keyword")

    for node_info in iter_keyword_node_info:
        node = node_info.node
        stack = [node]
        for token in _iter_keyword_arguments_tokens(node, tokenize_keyword_name=True):
            iter_in = _tokenize_subvars(token)

            try:
                # The first one is the variable store (the other is the
                # variable load on a default argument)
                # We are only interested in the second in this API.
                next(iter_in)
            except StopIteration:
                continue

            for t, varid in iter_in:
                if t.type != t.VARIABLE:
                    continue
                if not _add_match(found, t):
                    continue
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


def is_keyword_usage_node(ast):
    return (
        ast.__class__.__name__
        in _CLASSES_KEYWORDS_AND_OTHERS_WITH_ARGUMENTS_AS_KEYWORD_CALLS
    )


@_convert_ast_to_indexer
def _iter_node_info_which_may_have_usage_info(ast):
    for clsname in _CLASSES_KEYWORDS_AND_OTHERS_WITH_ARGUMENTS_AS_KEYWORD_CALLS:
        yield from ast.iter_indexed(clsname)


def _iter_keyword_usage_tokens_uncached(
    ast, collect_args_as_keywords: bool
) -> Iterator[KeywordUsageInfo]:
    from robotframework_ls.impl.ast_utils_keyword_usage import (
        obtain_keyword_usage_handler,
    )

    for node_info in _iter_node_info_which_may_have_usage_info(ast):
        stack = node_info.stack
        node = node_info.node
        keyword_usage_handler = obtain_keyword_usage_handler(
            stack, node, recursive=collect_args_as_keywords
        )
        if keyword_usage_handler is not None:
            yield from keyword_usage_handler.iter_keyword_usages_from_node()


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
        from robotframework_ls.impl.ast_utils_keyword_usage import (
            obtain_keyword_usage_for_token,
        )

        return obtain_keyword_usage_for_token(stack, node, token)

    from robotframework_ls.impl.ast_utils_keyword_usage import (
        _create_root_keyword_usage_info,
    )

    return _create_root_keyword_usage_info(stack, node)


def get_keyword_name_token(
    stack: Tuple[INode, ...],
    node: INode,
    token: IRobotToken,
    accept_only_over_keyword_name: bool = True,
) -> Optional[IRobotToken]:
    """
    If the given token is a keyword call name, return the token, otherwise return None.

    :param accept_only_over_keyword_name:
        If True we'll only accept the token if it's over the keyword name.
        If False we'll accept the token even if it's over a keyword parameter.

    :note: this goes hand-in-hand with iter_keyword_usage_tokens.
    """
    if token.type == token.KEYWORD or (
        token.type == token.NAME
        and node.__class__.__name__ in CLASSES_WITH_ARGUMENTS_AS_KEYWORD_CALLS_AS_SET
    ):
        locinfo = get_localization_info_from_model(stack[0])
        return _strip_token_bdd_prefix(token, locinfo)[1]

    if token.type == token.ARGUMENT and not token.value.strip().endswith("}"):
        from robotframework_ls.impl.ast_utils_keyword_usage import (
            obtain_keyword_usage_for_token,
        )

        keyword_usage = obtain_keyword_usage_for_token(stack, node, token)
        if keyword_usage is not None:
            if accept_only_over_keyword_name:
                if _same_line_col(keyword_usage.token, token):
                    return token
            else:
                return keyword_usage.token
    return None


def get_library_import_name_token(
    node, token: IRobotToken, generate_empty_on_eol=False
) -> Optional[IRobotToken]:
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

    if generate_empty_on_eol:
        if token.type == token.EOL and isinstance_name(node, "LibraryImport"):
            if len(node.tokens) == 2:
                # i.e.: just `Library   EOL`
                return create_empty_token_name_at_eol(token)
    return None


def create_empty_token_name_at_eol(token):
    # i.e.: just `Library   EOL`
    l = len(token.value)
    if token.value.endswith("\r\n"):
        l -= 2
    elif token.value.endswith("\r") or token.value.endswith("\n"):
        l -= 1
    return copy_token_with_subpart(token, l, l, token.NAME)


def get_resource_import_name_token(
    node, token: IRobotToken, generate_empty_on_eol=False
) -> Optional[IRobotToken]:
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

    if generate_empty_on_eol:
        if token.type == token.EOL and isinstance_name(node, "ResourceImport"):
            if len(node.tokens) == 2:
                # i.e.: just `Library   EOL`
                return create_empty_token_name_at_eol(token)
    return None


def get_variables_import_name_token(node, token, generate_empty_on_eol=False):
    """
    If the given ast node is a variables import and the token is its name, return
    the name token, otherwise, return None.
    """

    if (
        token.type == token.NAME
        and isinstance_name(node, "VariablesImport")
        and node.name == token.value  # I.e.: match the name, not the alias.
    ):
        return token

    if generate_empty_on_eol:
        if token.type == token.EOL and isinstance_name(node, "VariablesImport"):
            if len(node.tokens) == 2:
                # i.e.: just `Library   EOL`
                return create_empty_token_name_at_eol(token)
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


def _strip_node_and_token_bdd_prefix(
    stack: List[INode],
    node: INode,
    token_type: str,
) -> Tuple[str, INode, Optional[IRobotToken]]:
    """
    This is a workaround because the parsing does not separate a BDD prefix from
    the keyword name. If the parsing is improved to do that separation in the future
    we can stop doing this.
    """
    original_token = node.get_token(token_type)
    if original_token is None:
        return "", node, None

    locinfo = get_localization_info_from_model(stack[0])
    prefix, token = _strip_token_bdd_prefix(original_token, locinfo)
    if token is original_token:
        # i.e.: No change was done.
        return prefix, node, token
    return prefix, _copy_of_node_replacing_token(node, token, token_type), token


def _strip_token_bdd_prefix(
    token: IRobotToken, locinfo: LocalizationInfo
) -> Tuple[str, IRobotToken]:
    """
    This is a workaround because the parsing does not separate a BDD prefix from
    the keyword name. If the parsing is improved to do that separation in the future
    we can stop doing this.

    :return: the prefix and a new token with the bdd prefix stripped or the
    original token passed (if no prefix was detected).
    """
    from robot.api import Token

    assert token is not None

    text = token.value.lower()
    for prefix in locinfo.iter_bdd_prefixes_on_read():
        if text.startswith(prefix):
            try:
                next_is_space = text[len(prefix)] == " "
            except IndexError:
                continue

            if next_is_space:
                new_name = token.value[len(prefix) + 1 :]
                return prefix, Token(
                    type=token.type,
                    value=new_name,
                    lineno=token.lineno,
                    col_offset=token.col_offset + len(prefix) + 1,
                    error=token.error,
                )
    return "", token


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


def copy_token_with_subpart(token, start, end, token_type=None):
    from robot.api import Token

    if token_type is None:
        token_type = token.type

    return Token(
        type=token_type,
        value=token.value[start:end],
        lineno=token.lineno,
        col_offset=token.col_offset + start,
        error=token.error,
    )


def copy_token_with_subpart_up_to_col(token, column):
    return copy_token_with_subpart(token, 0, column)


def create_range_from_token(token: IRobotToken) -> RangeTypedDict:
    start: PositionTypedDict = {"line": token.lineno - 1, "character": token.col_offset}
    end: PositionTypedDict = {
        "line": token.lineno - 1,
        "character": token.end_col_offset,
    }
    taken_range: RangeTypedDict = {"start": start, "end": end}
    return taken_range


def create_range_from_tokens(
    token: IRobotToken, end_token: IRobotToken
) -> RangeTypedDict:
    start: PositionTypedDict = {"line": token.lineno - 1, "character": token.col_offset}
    end: PositionTypedDict = {
        "line": end_token.lineno - 1,
        "character": end_token.end_col_offset,
    }
    taken_range: RangeTypedDict = {"start": start, "end": end}
    return taken_range


def create_range_from_node(node: INode, accept_empty=True) -> Optional[RangeTypedDict]:
    first_token = None
    last_found_tokens = None

    # Find the first token
    for n in itertools.chain(
        iter((node,)), (x[1] for x in _iter_nodes(node, recursive=True))
    ):
        try:
            last_found_tokens = n.tokens
        except AttributeError:
            continue

        if not last_found_tokens:
            continue

        if accept_empty:
            first_token = next(iter(last_found_tokens))
        else:
            for t in last_found_tokens:
                if t.type in (t.EOL, t.EOS, t.SEPARATOR):
                    continue
                first_token = t
                break

        if first_token is not None:
            break

    if first_token is None:
        return None

    # Ok, we found the first one, now, let's find the last one.
    last_token = None
    last_found_tokens = None

    for n in itertools.chain(iter((node,)), _iter_nodes_reverse(node)):
        try:
            last_found_tokens = n.tokens
        except AttributeError:
            continue

        if not last_found_tokens:
            continue

        if accept_empty:
            last_token = next(reversed(last_found_tokens))
        else:
            for t in reversed(last_found_tokens):
                if t.type in (t.EOL, t.EOS, t.SEPARATOR):
                    continue
                last_token = t
                break

        if last_token is not None:
            break

    if last_token is None:
        return None

    return create_range_from_tokens(first_token, last_token)


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


def iter_expression_variables(
    expression_token: IRobotToken,
) -> Iterator[Tuple[IRobotToken, AdditionalVarInfo]]:
    from robot.api import Token

    for tok, var_info in iter_expression_tokens(expression_token):
        if tok.type == Token.VARIABLE:
            yield tok, var_info


class RobotMatchTokensGenerator:
    def __init__(self, token, default_type: str):
        self.default_type = default_type
        self.token = token
        self.last_gen_end_offset = 0

    def gen_type(self, op_type: str, until_offset: int):
        token = self.token
        if until_offset > self.last_gen_end_offset:
            from robot.api import Token

            val = token.value[self.last_gen_end_offset : until_offset]
            if val.strip():  # Don't generate just for whitespaces.
                yield (
                    Token(
                        op_type,
                        val,
                        token.lineno,
                        token.col_offset + self.last_gen_end_offset,
                        token.error,
                    ),
                    AdditionalVarInfo(),
                )
            self.last_gen_end_offset = until_offset

    def gen_default_type(
        self, until_offset: int
    ) -> Iterable[Tuple[IRobotToken, AdditionalVarInfo]]:
        yield from self.gen_type(self.default_type, until_offset)

    def gen_tokens_from_robot_match(
        self,
        robot_match: IRobotVariableMatch,
        last_relative_index: int,
        op_type: str = "variableOperator",
        var_type: Optional[str] = None,
    ) -> Iterable[Tuple[IRobotToken, AdditionalVarInfo]]:
        from robot.api import Token
        from robotframework_ls.impl.variable_resolve import is_number_var
        from robotframework_ls.impl.variable_resolve import is_python_eval_var
        from robotframework_ls.impl.variable_resolve import (
            extract_var_name_from_extended_base_name,
        )
        from robotframework_ls.impl.variable_resolve import robot_search_variable

        curr_var_type = var_type
        if curr_var_type is None:
            curr_var_type = Token.VARIABLE

        token = self.token
        if not robot_match.base:
            i = token.value.find("{", robot_match.start + last_relative_index) + 1
        else:
            i = token.value.find(
                robot_match.base, robot_match.start + last_relative_index
            )

        start_offset = robot_match.start + last_relative_index

        yield from self.gen_default_type(start_offset)

        yield (
            Token(
                op_type,
                token.value[robot_match.start + last_relative_index : i],
                token.lineno,
                token.col_offset + start_offset,
                token.error,
            ),
            AdditionalVarInfo(),
        )

        # Base has everything
        base = robot_match.base
        assert base is not None

        first_subvar_match_in_base = robot_search_variable(base)
        has_subvar = bool(
            first_subvar_match_in_base and first_subvar_match_in_base.base
        )

        # Now, we must extract the variable name from the base.
        # ie.: ${a + 1} will provide 'a'.
        var_name_from_base = ""
        if not is_number_var(base) and not is_python_eval_var(base):
            var_name_from_base = extract_var_name_from_extended_base_name(base)
            if var_name_from_base != base:
                while var_name_from_base.endswith((" ", "\t")):
                    var_name_from_base = var_name_from_base[:-1]

        base_or_extended_part = base
        offset = token.col_offset + i
        if var_name_from_base or not base_or_extended_part.strip():
            if not has_subvar or (
                first_subvar_match_in_base
                and first_subvar_match_in_base.start > len(var_name_from_base)
            ):
                base_or_extended_part = base[len(var_name_from_base) :]
                offset += len(var_name_from_base)
                yield (
                    Token(
                        Token.VARIABLE,
                        var_name_from_base,
                        token.lineno,
                        token.col_offset + i,
                        token.error,
                    ),
                    AdditionalVarInfo(
                        robot_match.identifier, extended_part=base_or_extended_part
                    ),
                )

        if base_or_extended_part.strip():
            subvar_tokens = tuple(
                _tokenize_subvars_tokens(
                    Token(
                        curr_var_type,
                        base_or_extended_part,
                        token.lineno,
                        offset,
                        token.error,
                    ),
                    op_type,
                    var_type,
                )
            )

            yield from iter(subvar_tokens)

        j = i + len(base)
        self.last_gen_end_offset = j

        for item in robot_match.items:
            item_index = token.value.find(item, self.last_gen_end_offset)
            if item_index >= 0:
                if "{" in item:
                    yield from self.gen_type(op_type, item_index)

                    subvar_tokens = tuple(
                        _tokenize_subvars_tokens(
                            Token(
                                Token.VARIABLE,
                                item,
                                token.lineno,
                                token.col_offset + item_index,
                                token.error,
                            ),
                            op_type,
                            var_type,
                        )
                    )

                    yield from iter(subvar_tokens)

        yield from self.gen_type(op_type, robot_match.end + last_relative_index)


def _gen_tokens_in_py_expr(
    py_expr,
    expression_token,
) -> Iterator[Tuple[IRobotToken, AdditionalVarInfo]]:
    from tokenize import generate_tokens, NAME, ERRORTOKEN
    from io import StringIO
    from robot.api import Token

    var_type = Token.VARIABLE
    op_type = "variableOperator"

    gen_var_token_info = None
    try:
        for token_info in generate_tokens(StringIO(py_expr).readline):
            if token_info.type == ERRORTOKEN and token_info.string == "$":
                gen_var_token_info = token_info

            elif gen_var_token_info is not None and token_info.type == NAME:
                if gen_var_token_info.start[1] == token_info.start[1] - 1:
                    start_offset = gen_var_token_info.start[1]

                    yield (
                        Token(
                            op_type,
                            gen_var_token_info.string,
                            expression_token.lineno,
                            expression_token.col_offset + start_offset,
                            expression_token.error,
                        ),
                        AdditionalVarInfo(context=AdditionalVarInfo.CONTEXT_EXPRESSION),
                    )

                    yield (
                        Token(
                            var_type,
                            token_info.string,
                            expression_token.lineno,
                            expression_token.col_offset + token_info.start[1],
                            expression_token.error,
                        ),
                        AdditionalVarInfo(
                            "$", context=AdditionalVarInfo.CONTEXT_EXPRESSION
                        ),
                    )

    except:
        log.exception(f"Unable to evaluate python expression from: {expression_token}")


def iter_expression_tokens(
    expression_token: IRobotToken,
    default_type=None,
) -> Iterator[Tuple[IRobotToken, AdditionalVarInfo]]:
    # See: robot.variables.evaluation.evaluate_expression

    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches

    if default_type is None:
        default_type = expression_token.ARGUMENT

    expression_to_evaluate: List[str] = []

    robot_matches_and_relative_index = list(
        iter_robot_variable_matches(expression_token.value)
    )

    robot_match = None
    for robot_match, relative_index in robot_matches_and_relative_index:
        expression_to_evaluate.append(robot_match.before)
        expression_to_evaluate.append("1" * (robot_match.end - robot_match.start))

    if robot_match is None:
        after = expression_token.value
    else:
        after = robot_match.after

    if after.strip():
        expression_to_evaluate.append(after)

    python_toks_and_identifiers: list = []
    if expression_to_evaluate:
        expr = "".join(expression_to_evaluate)
        if expr.strip():
            python_toks_and_identifiers.extend(
                _gen_tokens_in_py_expr(expr, expression_token)
            )

    robot_match_generator = RobotMatchTokensGenerator(expression_token, default_type)

    # Now, let's put the vars from python and the robot matches we have in a
    # sorted list so that we can iterate properly.
    from robot.api import Token

    def key(obj):
        # obj is either a tuple(robot match/relative index) or a tuple(Token/var identifier)
        if isinstance(obj[0], Token):
            return obj[0].col_offset

        robot_match: IRobotVariableMatch = obj[0]
        relative_index = obj[1]
        return relative_index + robot_match.start + expression_token.col_offset

    lst = sorted(
        python_toks_and_identifiers + robot_matches_and_relative_index, key=key
    )

    # obj is either a tuple(robot match/relative index) or a tuple(Token/var identifier)
    obj: Any
    for obj in lst:
        if isinstance(obj[0], Token):
            yield from robot_match_generator.gen_default_type(
                obj[0].col_offset - expression_token.col_offset
            )
            yield obj
            robot_match_generator.last_gen_end_offset = (
                obj[0].end_col_offset - expression_token.col_offset
            )

        else:
            yield from robot_match_generator.gen_tokens_from_robot_match(*obj)
    yield from robot_match_generator.gen_default_type(len(expression_token.value))


def is_node_with_expression_argument(node) -> bool:
    if node.__class__.__name__ == "KeywordCall":
        kw_name = node.keyword
        return kw_name and normalize_robot_name(kw_name) == "evaluate"
    else:
        return node.__class__.__name__ in CLASSES_WTH_EXPRESSION_ARGUMENTS


def iter_arguments_from_template(
    stack: Tuple[INode, ...], node: INode
) -> Iterator[NodeInfo]:
    if not stack:
        log.critical(
            "Unable to iterate arguments from template because the stack is empty."
        )
        return

    from robot.api import Token

    if node.type == Token.TEMPLATE:
        for entry in reversed(stack):
            if isinstance_name(entry, "TestCase"):
                for node_info in iter_indexed(entry, "TemplateArguments"):
                    for token in node_info.node.tokens:
                        if token.type == token.ARGUMENT:
                            yield node_info
                            break
        return

    if node.type == Token.TEST_TEMPLATE:
        # We need to collect all the TemplateArguments and skip the ones from
        # tests which have a customized template.
        for node_info in iter_indexed(stack[0], "TestCase"):
            if tuple(iter_indexed(node_info.node, "Template")):
                # i.e.: This test case has a custom template
                continue

            for node_info in iter_indexed(node_info.node, "TemplateArguments"):
                for token in node_info.node.tokens:
                    if token.type == token.ARGUMENT:
                        yield node_info
                        break


def set_localization_info_in_model(ast, localization_info: LocalizationInfo):
    """
    Sets information regarding localization of the AST in the model (File).
    """
    assert (
        ast.__class__.__name__ == "File"
    ), f"Expected File. Found: {ast.__class__.__name__}"

    ast.__localization_info__ = localization_info

    file_weak_ref = weakref.ref(ast)
    for _stack, node in _iter_nodes(ast):
        node.__file_weak_ref__ = file_weak_ref  # type:ignore
        node.__localization_info__ = localization_info  # type:ignore


def get_localization_info_from_model(ast) -> LocalizationInfo:
    """
    Note that the ast should usually be the file or one of the sections right
    below it (such as the settings) where the localization info was set (usually
    it's the stack[0] passed with the node).
    """
    return ast.__localization_info__


def iter_argument_tokens(ast) -> Iterator[INode]:
    for token in ast.tokens:
        if token.type == token.ARGUMENT:
            yield token
