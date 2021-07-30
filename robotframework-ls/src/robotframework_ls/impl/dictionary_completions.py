import re
from typing import Dict, List, Tuple
from robot.api import Token
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.lsp import (CompletionItem,
                                  MarkupKind,
                                  CompletionItemKind,
                                  InsertTextFormat,
                                  Position,
                                  Range,
                                  TextEdit)

log = get_logger(__name__)
_DICT_VARIABLE_REGEX = re.compile(r"[$|&]{([\w\s]+)}")
_DICT_KEY_REGEX = re.compile(r"\[([\w\s]*)\]")


def _get_variables(completion_context: ICompletionContext):
    variables = []
    for node_info in completion_context.get_all_variables():
        node = node_info.node
        token = node.get_token(Token.VARIABLE)
        if token is None:
            continue
        var_name = token.value
        var_value = node.value
        variables.append((var_name, var_value))
    return variables


def _get_dict_name(dict_item_access: str):
    dict_name = _DICT_VARIABLE_REGEX.findall(dict_item_access)
    return "&{" + dict_name.pop() + "}"


def _get_dict_keys(dict_item_access: str):
    dict_keys = _DICT_KEY_REGEX.findall(dict_item_access)
    dict_keys.reverse()
    return dict_keys


def _get_dictionary(variables: List[Tuple[str, List[str]]], dict_name: str, dict_items: List[str]):
    """
    Get the dictionary whose keys are the autocompletion options
    ${dict_name}([dict_key])*[<dictionary.keys()>]
    """
    for var_name, var_value in variables:
        if not var_name.startswith(dict_name):
            continue
        dictionary = _as_dictionary(var_value)
        dict_keys = dictionary.keys()
        dict_entry = dict_items.pop()
        if dict_entry == '':
            return dictionary
        matching_keys = [key for key in dict_keys if dict_entry in key]
        if len(matching_keys) == 0:
            return {}
        if len(matching_keys) == 1 and dict_entry == matching_keys[0]:
            dict_value = dictionary[dict_entry]
            if dict_value.startswith("&"):
                dict_name = _get_dict_name(dict_value)
                dict_items += _get_dict_keys(dict_value)
                return _get_dictionary(variables, dict_name, dict_items)
            else:
                return {}
        else:
            return {key: dictionary[key] for key in matching_keys}
    return None


def _as_dictionary(dict_tokens: List[str]):
    """
    Parse ["key1=val1", "key2=val2",...] as a dictionary
    """
    dictionary = {}
    for token in dict_tokens:
        key, val = token.split("=")
        dictionary.update({key: val})
    return dictionary


def _completion_items(dictionary: Dict[str, str], editor_range: Range):
    return [CompletionItem(
             key,
             kind=CompletionItemKind.Variable,
             text_edit=TextEdit(editor_range, f"{key}]"),
             insertText=key,
             documentation=value,
             insertTextFormat=InsertTextFormat.Snippet,
             documentationFormat=MarkupKind.PlainText,
             ).to_dict() for key, value in dictionary.items()]


def complete(completion_context: ICompletionContext):
    token_info = completion_context.get_current_variable()
    if token_info is None:
        return []
    token = token_info.token
    value = token.value
    last_opening_bracket_column = value[::-1].index("[")
    variables = _get_variables(completion_context)
    for resource_doc in completion_context.get_resource_imports_as_docs():
        new_ctx = completion_context.create_copy(resource_doc)
        variables += _get_variables(new_ctx)
    dict_name = _get_dict_name(value)
    dict_keys = _get_dict_keys(value)
    dictionary = _get_dictionary(variables, dict_name, dict_keys)
    if dictionary is None:
        return []
    selection = completion_context.sel
    editor_range = Range(
        start=Position(selection.line, token.col_offset + len(value) - last_opening_bracket_column),
        end=Position(selection.line, token.end_col_offset),
    )
    return _completion_items(dictionary, editor_range)
