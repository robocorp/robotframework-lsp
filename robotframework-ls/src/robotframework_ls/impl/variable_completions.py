from robocorp_ls_core.cache import instance_cache
from robotframework_ls.impl.protocols import ICompletionContext, IRobotDocument
from robocorp_ls_core.robotframework_log import get_logger
from typing import Any

log = get_logger(__name__)


class IVariableFound(object):
    """
    :ivar variable_name:
    :ivar variable_value:
    :ivar completion_context:
        This may be a new completion context, created when a new document is
        being analyzed (the variable was created for that completion context).
    :ivar source:
        Source where the variable was found.
    :ivar lineno:
        Line where it was found (0-based). 
    """

    variable_name = ""
    variable_value = ""
    completion_context = None
    source = ""

    # Note: line/offsets 0-based.
    lineno = -1
    end_lineno = -1
    col_offset = -1
    end_col_offset = -1


class _VariableFoundFromToken(object):
    def __init__(
        self, completion_context, variable_token, variable_value, variable_name=None
    ):
        self.completion_context = completion_context
        self.variable_token = variable_token

        if variable_name is None:
            variable_name = str(variable_token)
        self.variable_name = variable_name
        if isinstance(variable_value, (list, tuple, set)):
            if len(variable_value) == 1:
                self.variable_value = str(next(iter(variable_value)))
            else:
                self.variable_value = str(variable_value)
        else:
            self.variable_value = str(variable_value)

    @property
    @instance_cache
    def source(self):
        from robocorp_ls_core import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def end_lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def col_offset(self):
        return self.variable_token.col_offset

    @property
    def end_col_offset(self):
        return self.variable_token.end_col_offset


class _VariableFoundFromPythonAst(object):
    def __init__(
        self,
        path: str,
        lineno: int,
        col: int,
        end_lineno: int,
        end_col: int,
        variable_value: str,
        variable_name: str,
    ):
        self.lineno = lineno
        self.col_offset = col
        self.end_lineno = end_lineno
        self.end_col_offset = end_col

        self.completion_context = None
        self._path = path
        self.variable_name = variable_name
        self.variable_value = variable_value

    @property
    @instance_cache
    def source(self):
        return self._path


class _VariableFoundFromSettings(object):
    def __init__(self, variable_name, variable_value):
        self.completion_context = None
        self.variable_name = variable_name
        self.variable_value = str(variable_value)

    @property
    @instance_cache
    def source(self):
        return ""

    @property
    def lineno(self):
        return 0

    @property
    def end_lineno(self):
        return 0

    @property
    def col_offset(self):
        return 0

    @property
    def end_col_offset(self):
        return 0


class _VariableFoundFromBuiltins(_VariableFoundFromSettings):
    pass


class _VariableFoundFromYaml(_VariableFoundFromSettings):
    pass


class _Collector(object):
    def __init__(self, selection, token, matcher):
        self.matcher = matcher
        self.completion_items = []
        self.selection = selection
        self.token = token

    def _create_completion_item_from_variable(self, variable_found, selection, token):
        """
        :param IVariableFound variable_found:
        :param selection:
        :param token:
        """
        from robocorp_ls_core.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robocorp_ls_core.lsp import MarkupKind
        from robocorp_ls_core.lsp import CompletionItemKind

        label = variable_found.variable_name
        text = label
        text = text.replace("$", "\\$")

        text_edit = TextEdit(
            Range(
                start=Position(selection.line, token.col_offset),
                end=Position(selection.line, token.end_col_offset),
            ),
            text,
        )

        # text_edit = None
        return CompletionItem(
            variable_found.variable_name,
            kind=CompletionItemKind.Variable,
            text_edit=text_edit,
            insertText=label,
            documentation=variable_found.variable_value,
            insertTextFormat=InsertTextFormat.Snippet,
            documentationFormat=MarkupKind.PlainText,
        ).to_dict()

    def accepts(self, variable_name):
        return self.matcher.accepts(variable_name)

    def on_variable(self, variable_found):
        self.completion_items.append(
            self._create_completion_item_from_variable(
                variable_found, self.selection, self.token
            )
        )


def _collect_completions_from_ast(
    ast, completion_context: ICompletionContext, collector
):
    completion_context.check_cancelled()
    from robot.api import Token

    for variable_node_info in completion_context.get_all_variables():
        variable_node = variable_node_info.node
        token = variable_node.get_token(Token.VARIABLE)
        if token is None:
            continue
        name = token.value
        if not name:
            continue
        name = name.strip()
        if not name:
            continue
        if name.endswith("="):
            name = name[:-1].rstrip()

        if name.startswith(("&", "@")):
            # Allow referencing dict(&)/list(@) variables as regular ($) variables
            dict_or_list_var = "$" + name[1:]
            if collector.accepts(dict_or_list_var):
                variable_found = _VariableFoundFromToken(
                    completion_context,
                    token,
                    variable_node.value,
                    variable_name=dict_or_list_var,
                )
                collector.on_variable(variable_found)
        if collector.accepts(name):
            variable_found = _VariableFoundFromToken(
                completion_context, token, variable_node.value, variable_name=name
            )
            collector.on_variable(variable_found)


def _collect_current_doc_variables(
    completion_context: ICompletionContext, collector: _Collector
):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, collector)


def _collect_resource_imports_variables(
    completion_context: ICompletionContext, collector: _Collector
):
    resource_doc: IRobotDocument
    for resource_doc in completion_context.get_resource_imports_as_docs():
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_following_imports(new_ctx, collector)


def _collect_variable_imports_variables(
    completion_context: ICompletionContext, collector: _Collector
):
    variable_import_doc: IRobotDocument
    for variable_import_doc in completion_context.get_variable_imports_as_docs():
        try:
            if variable_import_doc.path.lower().endswith(".py"):
                python_ast = variable_import_doc.get_python_ast()
                if python_ast is not None:
                    import ast as ast_module

                    for node in python_ast.body:
                        if isinstance(node, ast_module.Assign):
                            for target in node.targets:
                                if isinstance(target, ast_module.Name):
                                    varname = "${%s}" % (target.id,)
                                    if collector.accepts(varname):
                                        value = ""
                                        try:
                                            # Only available for Python 3.8 onwards...
                                            end_lineno = getattr(
                                                node.value, "end_lineno", None
                                            )
                                            if end_lineno is None:
                                                end_lineno = node.value.lineno

                                            # Only available for Python 3.8 onwards...
                                            end_col_offset = getattr(
                                                node.value, "end_col_offset", None
                                            )
                                            if end_col_offset is None:
                                                end_col_offset = 99999999
                                            value = variable_import_doc.get_range(
                                                node.value.lineno - 1,
                                                node.value.col_offset,
                                                end_lineno - 1,
                                                end_col_offset,
                                            )
                                        except:
                                            log.exception()

                                        variable_found = _VariableFoundFromPythonAst(
                                            variable_import_doc.path,
                                            target.lineno - 1,
                                            target.col_offset,
                                            target.lineno - 1,
                                            target.col_offset + len(target.id),
                                            value,
                                            variable_name=varname,
                                        )
                                        collector.on_variable(variable_found)

            elif variable_import_doc.path.lower().endswith(".yaml"):
                contents = variable_import_doc.get_yaml_contents()
                if isinstance(contents, dict):
                    for key, val in contents.items():
                        key = "${%s}" % (key,)
                        if collector.accepts(key):
                            collector.on_variable(_VariableFoundFromYaml(key, str(val)))

        except:
            log.exception()


def _collect_following_imports(
    completion_context: ICompletionContext, collector: _Collector
):
    completion_context.check_cancelled()
    if completion_context.memo.follow_import_variables(completion_context.doc.uri):
        # i.e.: prevent collecting variables for the same doc more than once.

        _collect_current_doc_variables(completion_context, collector)

        _collect_resource_imports_variables(completion_context, collector)

        _collect_variable_imports_variables(completion_context, collector)


def _collect_arguments(completion_context: ICompletionContext, collector: _Collector):
    from robotframework_ls.impl import ast_utils

    current_token_info = completion_context.get_current_token()
    if current_token_info is not None:
        stack = current_token_info.stack
        if stack:
            last_in_stack = stack[-1]
            for arg_token in ast_utils.iter_keyword_arguments_as_tokens(last_in_stack):
                name = str(arg_token)
                if collector.accepts(name):
                    variable_found = _VariableFoundFromToken(
                        completion_context, arg_token, "", variable_name=name
                    )
                    collector.on_variable(variable_found)


def _convert_name_to_var(variable_name):
    if not variable_name.strip().endswith("}"):
        variable_name = "${%s}" % (variable_name,)
    return variable_name


def _collect_from_settings(
    completion_context: ICompletionContext, collector: _Collector
):
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

    config = completion_context.config
    if config is not None:
        robot_variables = config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        for key, val in robot_variables.items():
            key = _convert_name_to_var(key)
            if collector.accepts(key):
                collector.on_variable(_VariableFoundFromSettings(key, val))


def _collect_from_builtins(
    completion_context: ICompletionContext, collector: _Collector
):
    from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES

    for key, val in BUILTIN_VARIABLES:
        key = _convert_name_to_var(key)
        if collector.accepts(key):
            collector.on_variable(_VariableFoundFromBuiltins(key, val))


def collect_variables(completion_context: ICompletionContext, collector: _Collector):
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None:
        if token_info.stack:
            stack_node = token_info.stack[-1]
        else:
            stack_node = completion_context.get_ast_current_section()
        for assign_node_info in ast_utils.iter_variable_assigns(stack_node):
            if collector.accepts(assign_node_info.token.value):
                rep = " ".join(tok.value for tok in assign_node_info.node.tokens)
                variable_found = _VariableFoundFromToken(
                    completion_context, assign_node_info.token, rep
                )
                collector.on_variable(variable_found)

    _collect_arguments(completion_context, collector)
    _collect_following_imports(completion_context, collector)
    _collect_from_settings(completion_context, collector)
    _collect_from_builtins(completion_context, collector)


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl.string_matcher import RobotStringMatcher

    token_info = completion_context.get_current_variable()
    if token_info is not None:
        token = token_info.token
        value = token.value
        if value.endswith("}"):
            value = value[:-1]
        collector = _Collector(completion_context.sel, token, RobotStringMatcher(value))
        collect_variables(completion_context, collector)
        return collector.completion_items
    return []
