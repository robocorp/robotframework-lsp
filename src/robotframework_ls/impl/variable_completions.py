from robotframework_ls import cache


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
    lineno = -1
    end_lineno = -1
    col_offset = -1
    end_col_offset = -1


class _VariableFound(object):
    def __init__(self, variable_node_info):
        self._variable_node = variable_node_info.node
        self.variable_name = self._variable_node.name
        self.variable_value = self._variable_node.value

    @property
    @cache.instance_cache
    def source(self):
        from robotframework_ls import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self._keyword_node.lineno - 1

    @property
    def end_lineno(self):
        return self._keyword_node.end_lineno - 1

    @property
    def col_offset(self):
        return self._keyword_node.col_offset

    @property
    def end_col_offset(self):
        return self._keyword_node.end_col_offset


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
        from robotframework_ls.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robotframework_ls.lsp import MarkupKind
        from robotframework_ls.lsp import CompletionItemKind

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

    ast = completion_context.get_ast()
    for variable_node_info in ast_utils.iter_variables(ast):
        if collector.accepts(variable_node_info.node.name):
            variable_found = _VariableFound(variable_node_info)
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
    for resource_doc in completion_context.iter_imports_docs():
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_following_imports(new_ctx, collector)


def _collect_following_imports(completion_context, collector):
    if completion_context.memo.follow_import_variables(completion_context.doc.uri):
        # i.e.: prevent collecting variables for the same doc more than once.

        _collect_current_doc_variables(completion_context, collector)

        _collect_resource_imports_variables(completion_context, collector)


def _collect_variables(completion_context, collector):
    _collect_following_imports(completion_context, collector)


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl.string_matcher import RobotStringMatcher

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = token_info.token
        if token.type == token.ARGUMENT:
            collector = _Collector(
                completion_context.sel, token, RobotStringMatcher(token.value)
            )
            _collect_variables(completion_context, collector)
            return collector.completion_items
    return []
