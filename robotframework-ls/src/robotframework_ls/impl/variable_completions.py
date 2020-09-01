from robocorp_ls_core.cache import instance_cache


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
        self.variable_value = variable_value

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


class _VariableFoundFromSettings(object):
    def __init__(self, variable_name, variable_value):
        self.variable_name = variable_name
        self.variable_value = variable_value

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


def _collect_completions_from_ast(ast, completion_context, collector):
    from robotframework_ls.impl import ast_utils
    from robot.api import Token

    ast = completion_context.get_ast()
    for variable_node_info in ast_utils.iter_variables(ast):
        variable_node = variable_node_info.node
        token = variable_node.get_token(Token.VARIABLE)
        if token is None:
            continue
        name = token.value
        if name.endswith("="):
            name = name[:-1].rstrip()

        if collector.accepts(name):
            variable_found = _VariableFoundFromToken(
                completion_context, token, variable_node.value, variable_name=name
            )
            collector.on_variable(variable_found)


def _collect_current_doc_variables(completion_context, collector):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, collector)


def _collect_resource_imports_variables(completion_context, collector):
    """
    :param CompletionContext completion_context:
    """
    for resource_doc in completion_context.get_resource_imports_as_docs():
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_following_imports(new_ctx, collector)


def _collect_following_imports(completion_context, collector):
    if completion_context.memo.follow_import_variables(completion_context.doc.uri):
        # i.e.: prevent collecting variables for the same doc more than once.

        _collect_current_doc_variables(completion_context, collector)

        _collect_resource_imports_variables(completion_context, collector)


def _collect_arguments(completion_context, collector):
    """
    :param CompletionContext completion_context:
    :param _Collector collector:
    """
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


def _collect_from_settings(completion_context, collector):
    """
    :param CompletionContext completion_context:
    :param _Collector collector:
    """
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

    config = completion_context.config
    if config is not None:
        robot_variables = config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        for key, val in robot_variables.items():
            key = _convert_name_to_var(key)
            if collector.accepts(key):
                collector.on_variable(_VariableFoundFromSettings(key, val))


def _collect_from_builtins(completion_context, collector):
    """
    :param CompletionContext completion_context:
    :param _Collector collector:
    """
    from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES

    for key, val in BUILTIN_VARIABLES:
        key = _convert_name_to_var(key)
        if collector.accepts(key):
            collector.on_variable(_VariableFoundFromBuiltins(key, val))


def collect_variables(completion_context, collector):
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
