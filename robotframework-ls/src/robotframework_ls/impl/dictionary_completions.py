import re
from robot.api import Token
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl import ast_utils
from robocorp_ls_core.lsp import (CompletionItem,
                                  MarkupKind,
                                  CompletionItemKind,
                                  InsertTextFormat,
                                  Position,
                                  Range,
                                  TextEdit)

log = get_logger(__name__)


def get_variables(completion_context):
    variables = []
    ast = completion_context.get_ast()
    for node_info in ast_utils.iter_variables(ast):
        node = node_info.node
        var_name = node.get_token(Token.VARIABLE).value
        var_value = node.value
        variables.append((var_name, var_value))
    return variables


def get_dict_name(dict_item_access):
    dict_variable_regex = re.compile(r"[$|&]{(\w+)}")
    dict_name = dict_variable_regex.findall(dict_item_access)
    return "&{" + dict_name.pop() + "}"


def get_dict_keys(dict_item_access):
    dict_key_regex = re.compile(r"\[([\w\s]*)\]")
    dict_keys = dict_key_regex.findall(dict_item_access)
    dict_keys.reverse()
    return dict_keys


def get_dictionary(variables, dict_name, dict_keys):
    """
    Get the dictionary whose keys are the autocompletion options
    ${dict_name}([dict_key])*[<dictionary.keys()>]
    """
    for var_name, var_value in variables:
        if var_name.startswith(dict_name):
            dictionary = as_dictionary(var_value)
            dict_entry = dict_keys.pop()
            if dict_entry == '':
                return dictionary
            else:
                dict_variable = dictionary[dict_entry]
                dict_name = get_dict_name(dict_variable)
                dict_keys += get_dict_keys(dict_variable)
                return get_dictionary(variables, dict_name, dict_keys)
    return None


def as_dictionary(dict_tokens):
    """
    Parse ["key1=val1", "key2=val2",...] as a dictionary
    """
    return dict([token.split("=") for token in dict_tokens])


def completion_items(dictionary, editor_range):
    return [CompletionItem(
             key,
             kind=CompletionItemKind.Variable,
             text_edit=TextEdit(editor_range, f"{key}]"),
             insertText=key,
             documentation=value,
             insertTextFormat=InsertTextFormat.Snippet,
             documentationFormat=MarkupKind.PlainText,
             ).to_dict() for key, value in dictionary.items()]


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    token_info = completion_context.get_current_variable()
    if token_info is None:
        return []
    token = token_info.token
    if not token.value.endswith("[]"):
        return []
    variables = get_variables(completion_context)
    for resource_doc in completion_context.get_resource_imports_as_docs():
        new_ctx = completion_context.create_copy(resource_doc)
        variables += get_variables(new_ctx)
    dict_name = get_dict_name(token.value)
    dict_keys = get_dict_keys(token.value)
    dictionary = get_dictionary(variables, dict_name, dict_keys)
    if dictionary is None:
        return []
    selection = completion_context.sel
    editor_range = Range(
        start=Position(selection.line, token.col_offset + len(token.value) - len("]")),
        end=Position(selection.line, token.end_col_offset),
    )
    return completion_items(dictionary, editor_range)
