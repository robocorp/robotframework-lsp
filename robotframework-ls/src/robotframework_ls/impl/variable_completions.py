from typing import Optional, List

from robocorp_ls_core.lsp import CompletionItemTypedDict
from robocorp_ls_core.protocols import check_implements, IDocumentSelection
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    IVariablesCollector,
    IVariableFound,
    IRobotToken,
    TokenInfo,
    AbstractVariablesCollector,
    VariableKind,
    VarTokenInfo,
)
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robotframework_ls.impl.variable_types import (
    VariableFoundFromToken,
    VariableFoundFromPythonAst,
    VariableFoundFromYaml,
    VariableFoundFromSettings,
    VariableFoundFromBuiltins,
)


log = get_logger(__name__)


class _Collector(AbstractVariablesCollector):
    def __init__(
        self, selection: IDocumentSelection, var_token_info: VarTokenInfo, matcher
    ):
        self.matcher = matcher
        self.completion_items: List[CompletionItemTypedDict] = []
        self.selection = selection
        self.token = var_token_info.token
        self.var_token_info = var_token_info

    def _create_completion_item_from_variable(
        self,
        variable_found: IVariableFound,
        selection: IDocumentSelection,
        token: IRobotToken,
    ) -> CompletionItemTypedDict:
        from robocorp_ls_core.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robocorp_ls_core.lsp import CompletionItemKind

        label = variable_found.variable_name

        if self.var_token_info.context == self.var_token_info.CONTEXT_EXPRESSION:
            # On expressions without '${...}' (just $var_name), we can't use spaces.
            label = label.replace(" ", "_")

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
            label,
            kind=CompletionItemKind.Variable,
            text_edit=text_edit,
            insertText=label,
            documentation=variable_found.variable_value,
            insertTextFormat=InsertTextFormat.Snippet,
        ).to_dict()

    def accepts(self, variable_name: str) -> bool:
        return self.matcher.accepts(variable_name)

    def on_variable(self, variable_found: IVariableFound):
        self.completion_items.append(
            self._create_completion_item_from_variable(
                variable_found, self.selection, self.token
            )
        )

    def __typecheckself__(self) -> None:
        _: IVariablesCollector = check_implements(self)


def _collect_completions_from_ast(
    ast, completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.variable_resolve import robot_search_variable

    completion_context.check_cancelled()
    from robot.api import Token

    for variable_node_info in completion_context.get_all_variables():
        variable_node = variable_node_info.node
        token = variable_node.get_token(Token.VARIABLE)
        if token is None:
            continue

        variable_match = robot_search_variable(token.value)
        # Filter out empty base
        if variable_match is None or not variable_match.base:
            continue

        if collector.accepts(variable_match.base):
            base_token = ast_utils.convert_variable_match_base_to_token(
                token, variable_match
            )
            variable_found = VariableFoundFromToken(
                completion_context,
                base_token,
                variable_node.value,
                variable_name=variable_match.base,
            )
            collector.on_variable(variable_found)

    accept_sets_in = {
        normalize_robot_name("Set Task Variable"),
        normalize_robot_name("Set Test Variable"),
        normalize_robot_name("Set Suite Variable"),
        normalize_robot_name("Set Global Variable"),
    }
    ast = completion_context.get_ast()
    for keyword_usage in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        if normalize_robot_name(keyword_usage.name) in accept_sets_in:
            var_name_tok = None
            var_value_tok = None
            for tok in keyword_usage.node.tokens:
                if tok.type == Token.ARGUMENT:
                    if var_name_tok is None:
                        var_name_tok = tok
                    else:
                        var_value_tok = tok
                        break

            if var_name_tok is not None:
                variable_match = robot_search_variable(var_name_tok.value)
                # Filter out empty base
                if variable_match is None or not variable_match.base:
                    continue

                if collector.accepts(variable_match.base):
                    base_token = ast_utils.convert_variable_match_base_to_token(
                        var_name_tok, variable_match
                    )
                    variable_value = ""
                    if var_value_tok is not None:
                        variable_value = var_value_tok.value

                    variable_found = VariableFoundFromToken(
                        completion_context,
                        base_token,
                        variable_value,
                        variable_name=variable_match.base,
                    )
                    collector.on_variable(variable_found)


def _collect_current_doc_variables(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, collector)


def _collect_resource_imports_variables(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    resource_doc: Optional[IRobotDocument]
    for _node, resource_doc in completion_context.get_resource_imports_as_docs():
        if resource_doc is None:
            continue
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_variables_from_document_context(new_ctx, collector)


def _collect_variables_from_variable_import_doc(
    variable_import_doc: IRobotDocument, collector: IVariablesCollector
):
    try:
        if variable_import_doc.path.lower().endswith(".py"):
            python_ast = variable_import_doc.get_python_ast()
            if python_ast is not None:
                import ast as ast_module

                for node in python_ast.body:
                    if isinstance(node, ast_module.Assign):
                        for target in node.targets:
                            if isinstance(target, ast_module.Name):
                                varname = target.id
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

                                    variable_found = VariableFoundFromPythonAst(
                                        variable_import_doc.path,
                                        target.lineno - 1,
                                        target.col_offset,
                                        target.lineno - 1,
                                        target.col_offset + len(target.id),
                                        value,
                                        variable_name=varname,
                                    )
                                    collector.on_variable(variable_found)

        elif variable_import_doc.path.lower().endswith((".yaml", ".yml")):
            dct_contents = variable_import_doc.get_yaml_contents()
            if isinstance(dct_contents, dict):
                if dct_contents:
                    try_to_compute_line = (
                        variable_import_doc.source.count("\n") * len(dct_contents)
                    ) <= 200
                    # Our (lame) algorithm to find a key will need to iterate
                    # over all lines for all entries, so, do it only for
                    # small docs (consider a better algorithm in the future)...
                    for initial_key, val in dct_contents.items():
                        key = initial_key

                        lineno = 0
                        if try_to_compute_line:
                            try:
                                # We don't have the real lineno during parsing,
                                # so, make a little hack to get something which
                                # may be close...
                                (
                                    lineno,
                                    _,
                                ) = variable_import_doc.get_last_line_col_with_contents(
                                    initial_key
                                )
                            except RuntimeError:
                                pass

                        if collector.accepts(key):
                            collector.on_variable(
                                VariableFoundFromYaml(
                                    key,
                                    str(val),
                                    source=variable_import_doc.path,
                                    lineno=lineno,
                                )
                            )

    except:
        log.exception()


def _collect_variables_from_document_context(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    completion_context.check_cancelled()
    _collect_current_doc_variables(completion_context, collector)

    if not only_current_doc:
        dependency_graph = completion_context.collect_dependency_graph()

        for resource_doc in completion_context.iter_dependency_and_init_resource_docs(
            dependency_graph
        ):
            new_ctx = completion_context.create_copy(resource_doc)
            _collect_current_doc_variables(new_ctx, collector)

        for node, variable_doc in dependency_graph.iter_all_variable_imports_as_docs():
            if variable_doc is None:
                # Note that 'None' documents will only be given for the
                # initial context (so, it's ok to use `completion_context`
                # in this case).
                from robot.api import Token

                node_name_tok = node.get_token(Token.NAME)
                if node_name_tok is not None:

                    (
                        _value,
                        token_errors,
                    ) = completion_context.token_value_and_unresolved_resolving_variables(
                        node_name_tok
                    )

                    if token_errors:
                        for token_error in token_errors:
                            collector.on_unresolved_variable_import(
                                completion_context,
                                node.name,
                                token_error.lineno,
                                token_error.lineno,
                                token_error.col_offset,
                                token_error.end_col_offset,
                                f"\nUnable to statically resolve variable: {token_error.value}.\nPlease set the `{token_error.value[2:-1]}` value in `robot.variables`.",
                            )

                    else:
                        collector.on_unresolved_variable_import(
                            completion_context,
                            node.name,
                            node_name_tok.lineno,
                            node_name_tok.lineno,
                            node_name_tok.col_offset,
                            node_name_tok.end_col_offset,
                            None,
                        )
                else:
                    collector.on_unresolved_variable_import(
                        completion_context,
                        node.name,
                        node.lineno,
                        node.end_lineno,
                        node.col_offset,
                        node.end_col_offset,
                        None,
                    )
                continue
            _collect_variables_from_variable_import_doc(variable_doc, collector)


def _collect_arguments(
    completion_context: ICompletionContext,
    node,
    collector: IVariablesCollector,
):
    from robotframework_ls.impl import ast_utils

    for arg_token, var_identifier in ast_utils.iter_keyword_arguments_as_tokens(
        node, tokenize_keyword_name=True
    ):
        name = arg_token.value
        if collector.accepts(name):
            variable_found = VariableFoundFromToken(
                completion_context,
                arg_token,
                "",
                variable_name=name,
                variable_kind=VariableKind.ARGUMENT,
            )
            collector.on_variable(variable_found)


def _collect_from_settings(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

    config = completion_context.config
    if config is not None:
        robot_variables = config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        for key, val in robot_variables.items():
            if collector.accepts(key):
                collector.on_variable(VariableFoundFromSettings(key, val))


def _collect_from_builtins(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl.robot_constants import get_builtin_variables

    for key, val in get_builtin_variables():
        if collector.accepts(key):
            collector.on_variable(VariableFoundFromBuiltins(key, val))


def collect_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    token_info = completion_context.get_current_token()
    if token_info is not None:
        collect_local_variables(completion_context, collector, token_info)

    collect_global_variables(completion_context, collector, only_current_doc)


def _collect_from_arguments_files(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    if not completion_context.variables_from_arguments_files_loader:
        return

    for c in completion_context.variables_from_arguments_files_loader:
        for variable in c.get_variables():
            if collector.accepts(variable.variable_name):
                collector.on_variable(variable)


def collect_global_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    _collect_variables_from_document_context(
        completion_context, collector, only_current_doc=only_current_doc
    )

    if not only_current_doc:
        _collect_from_settings(completion_context, collector)
        _collect_from_builtins(completion_context, collector)
        _collect_from_arguments_files(completion_context, collector)


def collect_local_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    token_info: TokenInfo,
):
    from robotframework_ls.impl import ast_utils

    if token_info.stack:
        for stack_node in reversed(token_info.stack):
            if stack_node.__class__.__name__ in ("Keyword", "TestCase"):
                break
        else:
            stack_node = token_info.stack[0]
    else:
        stack_node = completion_context.get_ast_current_section()

    for assign_node_info in ast_utils.iter_local_assigns(stack_node):
        completion_context.check_cancelled()
        if collector.accepts(assign_node_info.token.value):
            rep = " ".join(tok.value for tok in assign_node_info.node.tokens)
            variable_found = VariableFoundFromToken(
                completion_context, assign_node_info.token, rep
            )
            collector.on_variable(variable_found)

    _collect_arguments(completion_context, stack_node, collector)


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl.string_matcher import RobotStringMatcher

    var_token_info = completion_context.get_current_variable()
    if var_token_info is not None:
        value = var_token_info.token.value
        collector = _Collector(
            completion_context.sel, var_token_info, RobotStringMatcher(value)
        )
        only_current_doc = False
        if var_token_info.token.type == var_token_info.token.ASSIGN:
            # When assigning to variables we don't want to assign what's not
            # currently in this document (such as builtins).
            only_current_doc = True

        collect_variables(
            completion_context, collector, only_current_doc=only_current_doc
        )
        return collector.completion_items
    return []
