from typing import Dict, Tuple, Sequence, Iterator, List
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import ICompletionContext
from robocorp_ls_core.lsp import (
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
    Position,
    Range,
    TextEdit,
    CompletionItemTypedDict,
)

log = get_logger(__name__)


def _iter_normalized_variables_and_values(
    completion_context: ICompletionContext,
) -> Iterator[Tuple[str, Tuple[str, ...]]]:
    from robot.api import Token
    from robotframework_ls.impl.variable_resolve import robot_search_variable
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    for node_info in completion_context.get_all_variables():
        node = node_info.node
        token = node.get_token(Token.VARIABLE)
        if token is None:
            continue
        var_name = token.value
        robot_match = robot_search_variable(var_name)
        if robot_match and robot_match.base:
            # i.e.: Variable.value provides the values of the assign
            var_value: Tuple[str, ...] = node.value
            yield (normalize_robot_name(robot_match.base), var_value)


def _as_dictionary(
    dict_tokens: Sequence[str], normalize=False, filter_token: str = ""
) -> Dict[str, str]:
    """
    Parse ["key1=val1", "key2=val2",...] as a dictionary
    """
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    dictionary = {}
    for token in dict_tokens:
        key, val = token.split("=")
        if normalize:
            key = normalize_robot_name(key)
        if filter_token and filter_token not in normalize_robot_name(key):
            continue
        dictionary.update({key: val})
    return dictionary


def _completion_items(
    dictionary: Dict[str, str], editor_range: Range
) -> List[CompletionItemTypedDict]:
    return [
        CompletionItem(
            key,
            kind=CompletionItemKind.Variable,
            text_edit=TextEdit(editor_range, key),
            insertText=key,
            documentation=value,
            insertTextFormat=InsertTextFormat.Snippet,
        ).to_dict()
        for key, value in dictionary.items()
    ]


def _iter_all_normalized_variables_and_values(
    completion_context: ICompletionContext,
) -> Iterator[Tuple[str, Tuple[str, ...]]]:
    yield from _iter_normalized_variables_and_values(completion_context)

    dependency_graph = completion_context.collect_dependency_graph()
    for resource_doc in completion_context.iter_dependency_and_init_resource_docs(
        dependency_graph
    ):
        new_ctx = completion_context.create_copy(resource_doc)
        yield from _iter_normalized_variables_and_values(new_ctx)


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches
    from robotframework_ls.impl.ast_utils import iter_robot_match_as_tokens
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.variable_resolve import robot_search_variable

    token_info = completion_context.get_current_token()
    if token_info is None:
        return []
    token = token_info.token
    value = token.value

    col = completion_context.sel.col

    last_opening_bracket_column = -1

    items_seen = []

    prev_rtoken = None
    for robot_match, relative_index in iter_robot_variable_matches(value):
        robot_match_start = token.col_offset + relative_index + robot_match.start
        robot_match_end = token.col_offset + relative_index + robot_match.end

        if robot_match.base and robot_match_start < col < robot_match_end:
            # Now, let's see in which item/offset we're in.
            for rtoken in iter_robot_match_as_tokens(
                robot_match, relative_index=robot_match_start, lineno=token.lineno
            ):
                if rtoken.type == "[":
                    last_opening_bracket_column = rtoken.col_offset

                if rtoken.col_offset >= col:
                    if (
                        rtoken.type == "item"
                        and rtoken.col_offset == rtoken.end_col_offset
                    ):
                        # dealing with empty item at cursor
                        prev_rtoken = rtoken
                        items_seen.append(rtoken)

                    # The prev_rtoken is the one we're interested in
                    break

                if rtoken.type == "item":
                    items_seen.append(rtoken)

                prev_rtoken = rtoken

            break
    else:
        return []

    if prev_rtoken is None:
        return []

    if prev_rtoken.type not in ("[", "item"):
        return []

    if last_opening_bracket_column == -1:
        return []

    search_items_normalized = [normalize_robot_name(robot_match.base)]
    if len(items_seen) > 1:
        for item in items_seen[:-1]:
            # The last one is the one we're currently completing
            search_items_normalized.append(normalize_robot_name(item.value))

    selection = completion_context.sel

    if prev_rtoken.type == "[":
        start_offset = end_offset = prev_rtoken.col_offset
        filter_token = ""
    else:
        start_offset = prev_rtoken.col_offset
        end_offset = prev_rtoken.end_col_offset
        filter_token = normalize_robot_name(prev_rtoken.value)

    normalized_variables_and_values = dict(
        _iter_all_normalized_variables_and_values(completion_context)
    )

    last_dict = None
    count = 0
    while search_items_normalized:
        count += 1
        if count > 10:
            log.info(
                "Breaking up possible recursion on dictionary completions. Stack: %s",
                search_items_normalized,
            )
            return []
        search_name_normalized = search_items_normalized.pop(0)

        variable_values = normalized_variables_and_values.get(search_name_normalized)
        if not variable_values:
            return []
        if not search_items_normalized:
            dictionary = _as_dictionary(variable_values, filter_token=filter_token)
            editor_range = Range(
                start=Position(selection.line, start_offset),
                end=Position(selection.line, end_offset),
            )
            return _completion_items(dictionary, editor_range)
        else:
            last_dict = _as_dictionary(variable_values, normalize=True)

            next_search = last_dict.get(search_items_normalized.pop(0))
            if not next_search:
                return []

            if not next_search.startswith("&{"):
                return []

            new_match = robot_search_variable(next_search)
            if not new_match or not new_match.base:
                return []

            for it in reversed(new_match.items):
                search_items_normalized.insert(0, normalize_robot_name(it))
            search_items_normalized.insert(0, normalize_robot_name(new_match.base))

    return []
