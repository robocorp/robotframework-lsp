from typing import List, Optional, Dict, Iterator, Tuple

from robocorp_ls_core.lsp import LocationTypedDict, RangeTypedDict, PositionTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    IKeywordFound,
    IVariablesCollector,
    IVariableFound,
    cast_to_keyword_definition,
    AbstractVariablesCollector,
    cast_to_variable_definition,
    VarTokenInfo,
    VariableKind,
    KeywordUsageInfo,
)
import typing
from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.basic import isinstance_name, normalize_filename


log = get_logger(__name__)


def matches_source(s1: str, s2: str) -> bool:
    if s1 == s2:
        return True

    return normalize_filename(s1) == normalize_filename(s2)


class _VariableDefinitionsCollector(AbstractVariablesCollector):
    def __init__(self, robot_string_matcher):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        self.robot_string_matcher: RobotStringMatcher = robot_string_matcher
        self.matches: List[IVariableFound] = []

    def accepts(self, variable_name):
        return self.robot_string_matcher.is_variable_name_match(variable_name)

    def on_variable(self, variable_found: IVariableFound):
        self.matches.append(variable_found)

    def __typecheckself__(self) -> None:
        _: IVariablesCollector = check_implements(self)


def iter_variable_references_in_doc(
    completion_context: ICompletionContext,
    variable_found: IVariableFound,
    argument_var_references_computer: Optional[
        "_NamedArgumentVarReferencesComputer"
    ] = None,
) -> Iterator[RangeTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_range_from_token
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.variable_completions import collect_variables
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.variable_completions import collect_local_variables
    from robotframework_ls.impl.ast_utils import get_local_variable_stack_and_node

    normalized_name = normalize_robot_name(variable_found.variable_name)
    robot_string_matcher = RobotStringMatcher(normalized_name)

    # Collector for any variable with the same name.
    collector = _VariableDefinitionsCollector(robot_string_matcher)

    if argument_var_references_computer is None:
        argument_var_references_computer = _NamedArgumentVarReferencesComputer(
            completion_context, variable_found
        )

    if argument_var_references_computer.check_keyword_usage_normalized_name:
        lst = _PreventDuplicatesInList()
        argument_var_references_computer.add_references_to_named_keyword_arguments_from_doc(
            completion_context, lst
        )
        for entry in lst.lst:
            yield entry["range"]

    ast = completion_context.get_ast()
    if ast is not None:
        # Get references.
        var_token_info: VarTokenInfo
        if variable_found.is_local_variable:
            # For local variables we must have the stack
            stack = variable_found.stack
            assert stack

            # Just search the current stack.
            stack, stack_node = get_local_variable_stack_and_node(stack)

            for var_token_info in ast_utils.iter_variable_references(stack_node):
                completion_context.check_cancelled()

                if not robot_string_matcher.is_variable_name_match(
                    var_token_info.token.value
                ):
                    continue

                yield create_range_from_token(var_token_info.token)

            # Get definitions (only local).
            cp = completion_context.create_copy_with_selection(
                line=variable_found.lineno, col=variable_found.col_offset
            )
            token_info = cp.get_current_token()
            assert token_info
            collect_local_variables(cp, collector, token_info)

        else:
            # i.e.: For globals collect all globals as well as locals overriding
            # the global value.
            for var_token_info in ast_utils.iter_variable_references(ast):
                completion_context.check_cancelled()

                if not robot_string_matcher.is_variable_name_match(
                    var_token_info.token.value
                ):
                    continue

                yield create_range_from_token(var_token_info.token)

            # Get definitions (all).
            collect_variables(completion_context, collector, only_current_doc=True)

        variable: IVariableFound
        for variable in collector.matches:
            start: PositionTypedDict = {
                "line": variable.lineno,
                "character": variable.col_offset,
            }
            end: PositionTypedDict = {
                "line": variable.lineno,
                "character": variable.end_col_offset,
            }
            variable_range: RangeTypedDict = {"start": start, "end": end}
            yield variable_range


def iter_keyword_usage_references_in_doc(
    completion_context: ICompletionContext,
    doc: IRobotDocument,
    normalized_name: str,
    keyword_found: Optional[IKeywordFound],
) -> Iterator[Tuple[KeywordUsageInfo, bool, str, str]]:
    """
    :param keyword_found: if given, we'll match if the definition actually
    maps to the proper place (if not given, we'll just match based on the name
    without verifying if the definition is the same).
    """
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.find_definition import find_definition
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.text_utilities import matches_name_with_variables

    ast = doc.get_ast()
    if ast is not None:
        has_var_in_name = "{" in normalized_name

        # Dict with normalized name -> whether it was found or not previously.
        found_in_this_doc: Dict[str, bool] = {}

        # Ok, we have the document, now, load the usages.
        for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
            ast, collect_args_as_keywords=True
        ):
            completion_context.check_cancelled()
            keword_name_possibly_dotted = keyword_usage_info.name
            found_dot_in_usage = "." in keword_name_possibly_dotted
            if found_dot_in_usage:
                keword_name_not_dotted = keword_name_possibly_dotted.split(".")[-1]
            else:
                keword_name_not_dotted = keword_name_possibly_dotted

            keword_name_not_dotted_normalized = normalize_robot_name(
                keword_name_not_dotted
            )
            if keword_name_not_dotted_normalized == normalized_name or (
                has_var_in_name
                and matches_name_with_variables(
                    keword_name_not_dotted_normalized, normalized_name
                )
            ):
                found_once_in_this_doc = found_in_this_doc.get(
                    keword_name_possibly_dotted
                )
                token = keyword_usage_info.token

                line = token.lineno - 1

                if keyword_found is not None:
                    if found_once_in_this_doc is None:
                        # Verify if it's actually the same one (not one defined in
                        # a different place with the same name).

                        new_ctx = completion_context.create_copy_doc_line_col(
                            doc, line, token.col_offset
                        )
                        definitions = find_definition(new_ctx)
                        for definition in definitions:
                            found = matches_source(
                                definition.source, keyword_found.source
                            )

                            if found:
                                found_once_in_this_doc = found_in_this_doc[
                                    keword_name_possibly_dotted
                                ] = True
                                break
                        else:
                            found_once_in_this_doc = found_in_this_doc[
                                keword_name_possibly_dotted
                            ] = False
                            continue

                    if not found_once_in_this_doc:
                        continue

                yield (
                    keyword_usage_info,
                    found_dot_in_usage,
                    keword_name_possibly_dotted,
                    keword_name_not_dotted,
                )


def iter_keyword_references_in_doc(
    completion_context: ICompletionContext,
    doc: IRobotDocument,
    normalized_name: str,
    keyword_found: Optional[IKeywordFound],
) -> Iterator[RangeTypedDict]:
    for (
        keyword_usage_info,
        found_dot_in_usage,
        keword_name_possibly_dotted,
        keword_name_not_dotted,
    ) in iter_keyword_usage_references_in_doc(
        completion_context, doc, normalized_name, keyword_found
    ):
        token = keyword_usage_info.token

        line = token.lineno - 1

        token = keyword_usage_info.token
        if found_dot_in_usage:
            # We need to create a new token because we just want to match the name part.
            col_offset = token.col_offset + (
                len(keword_name_possibly_dotted) - len(keword_name_not_dotted)
            )
            end_col_offset = token.end_col_offset
        else:
            col_offset = token.col_offset
            end_col_offset = token.end_col_offset

        # Ok, we found it, let's add it to the result.
        yield {
            "start": {
                "line": line,
                "character": col_offset,
            },
            "end": {
                "line": line,
                "character": end_col_offset,
            },
        }


def collect_variable_references(
    completion_context: ICompletionContext, var_token_info: VarTokenInfo
):
    from robotframework_ls.impl.find_definition import find_variable_definition

    var_definitions = find_variable_definition(completion_context, var_token_info)
    if not var_definitions:
        return []

    variable_found_lst: List[IVariableFound] = []

    for var_definition in var_definitions:
        as_variable_definition = cast_to_variable_definition(var_definition)
        if as_variable_definition:
            v = as_variable_definition.variable_found
            variable_found_lst.append(v)

    if not variable_found_lst:
        return []

    for v in variable_found_lst:
        if not v.is_local_variable:
            # I.e.: prefer globals (in which case we'll also collect shadowed
            # assigns in local scopes).
            variable_found = v
            break
    else:
        variable_found = next(iter(variable_found_lst))

    return _references_for_variable_found(completion_context, variable_found)


def references(
    completion_context: ICompletionContext, include_declaration: bool
) -> List[LocationTypedDict]:
    var_token_info = completion_context.get_current_variable()
    if var_token_info is not None:
        return collect_variable_references(completion_context, var_token_info)

    token_info = completion_context.get_current_token()
    if token_info is None:
        return []

    keyword_found: IKeywordFound
    if token_info.token.type == token_info.token.KEYWORD_NAME:
        if isinstance_name(token_info.node, "KeywordName"):
            from robotframework_ls.impl.find_definition import find_keyword_definition

            definitions = find_keyword_definition(completion_context, token_info)
            if definitions:
                for definition in definitions:
                    as_keyword_definition = cast_to_keyword_definition(definition)
                    if as_keyword_definition:
                        keyword_found = as_keyword_definition.keyword_found
                        return references_for_keyword_found(
                            completion_context, keyword_found, include_declaration
                        )

    current_keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if current_keyword_definition_and_usage_info is not None:
        completion_context.monitor.check_cancelled()
        keyword_definition, _usage_info = current_keyword_definition_and_usage_info

        keyword_found = keyword_definition.keyword_found
        return references_for_keyword_found(
            completion_context, keyword_found, include_declaration
        )

    return []


class _NamedArgumentVarReferencesComputer:
    """
    A helper to handle the case where we also need to rename named arguments.

    To do this we need to:
    1. Get references to the keyword
    2. Check if any of its arguments has something as 'var_name=xxx'.
    3. Create the reference to the 'var_name'.
    """

    def __init__(
        self,
        initial_completion_context: ICompletionContext,
        variable_found: IVariableFound,
    ):
        from robotframework_ls.impl.ast_utils import get_local_variable_stack_and_node
        from robotframework_ls.impl.find_definition import find_keyword_definition
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        self.check_keyword_usage_keyword_found = None
        self.check_keyword_usage_normalized_name = None
        self.var_name_normalized = normalize_robot_name(variable_found.variable_name)

        if (
            variable_found.variable_kind == VariableKind.ARGUMENT
            and variable_found.stack
        ):
            _, keyword_or_test_case_node = get_local_variable_stack_and_node(
                variable_found.stack
            )
            if keyword_or_test_case_node.__class__.__name__ == "Keyword":
                cp = initial_completion_context.create_copy_with_selection(
                    keyword_or_test_case_node.lineno - 1,
                    keyword_or_test_case_node.col_offset,
                )
                cp_token_info = cp.get_current_token()
                if cp_token_info:
                    found = find_keyword_definition(
                        cp,
                        cp_token_info,
                    )

                    for keyword_found_definition in found or ():
                        self.check_keyword_usage_keyword_found = (
                            keyword_found_definition.keyword_found
                        )
                        self.check_keyword_usage_normalized_name = normalize_robot_name(
                            keyword_found_definition.keyword_name
                        )
                        break

    def add_references_to_named_keyword_arguments_from_doc(
        self,
        new_completion_context: ICompletionContext,
        ret: "_PreventDuplicatesInList",
    ):
        from robotframework_ls.impl.variable_resolve import find_split_index
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        if not self.check_keyword_usage_normalized_name:
            return

        for (
            keyword_usage_info,
            _found_dot_in_usage,
            _keword_name_possibly_dotted,
            _keword_name_not_dotted,
        ) in iter_keyword_usage_references_in_doc(
            new_completion_context,
            new_completion_context.doc,
            self.check_keyword_usage_normalized_name,
            self.check_keyword_usage_keyword_found,
        ):
            for token in keyword_usage_info.node.tokens:
                if token.type == token.ARGUMENT:
                    split_eq = find_split_index(token.value)
                    if split_eq > 0:
                        arg_name = normalize_robot_name(token.value[:split_eq])
                        if arg_name == self.var_name_normalized:
                            start: PositionTypedDict = {
                                "line": token.lineno - 1,
                                "character": token.col_offset,
                            }
                            end: PositionTypedDict = {
                                "line": token.lineno - 1,
                                "character": token.col_offset + split_eq,
                            }
                            ref_range: RangeTypedDict = {"start": start, "end": end}
                            ret.append(
                                {
                                    "uri": new_completion_context.doc.uri,
                                    "range": ref_range,
                                }
                            )


class _PreventDuplicatesInList:
    def __init__(self):
        self.lst: List[LocationTypedDict] = []
        self._found = set()

    def append(self, location: LocationTypedDict):
        key = (
            location["uri"],
            location["range"]["start"]["line"],
            location["range"]["start"]["character"],
            location["range"]["end"]["line"],
            location["range"]["end"]["character"],
        )
        if key in self._found:
            return
        self._found.add(key)
        self.lst.append(location)


def _references_for_variable_found(
    initial_completion_context: ICompletionContext,
    variable_found: IVariableFound,
):
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    ret = _PreventDuplicatesInList()

    is_local_variable = variable_found.is_local_variable

    from robotframework_ls.impl.workspace_symbols import iter_symbols_caches

    named_argument_var_references_computer = _NamedArgumentVarReferencesComputer(
        initial_completion_context, variable_found
    )

    # Initial doc (need to get local scope).
    ref_range: RangeTypedDict
    for ref_range in iter_variable_references_in_doc(
        initial_completion_context,
        variable_found,
        named_argument_var_references_computer,
    ):
        ret.append({"uri": initial_completion_context.doc.uri, "range": ref_range})

    if (
        is_local_variable
        and not named_argument_var_references_computer.check_keyword_usage_keyword_found
    ):
        return ret.lst

    normalized_variable_name = normalize_robot_name(variable_found.variable_name)

    for symbols_cache in iter_symbols_caches(
        None,
        initial_completion_context,
        force_all_docs_in_workspace=True,
        timeout=999999,
    ):
        initial_completion_context.check_cancelled()

        # If it's a local variable we may still need to search for named arguments...
        if (
            is_local_variable
            and named_argument_var_references_computer.check_keyword_usage_normalized_name
        ):
            if not symbols_cache.has_keyword_usage(
                named_argument_var_references_computer.check_keyword_usage_normalized_name
            ):
                continue

        elif not is_local_variable:
            if not symbols_cache.has_global_variable_definition(
                normalized_variable_name
            ) and not symbols_cache.has_variable_reference(normalized_variable_name):
                continue

        doc: Optional[IRobotDocument] = symbols_cache.get_doc()
        if doc is None:
            uri = symbols_cache.get_uri()
            if uri is None:
                continue

            doc = typing.cast(
                Optional[IRobotDocument],
                initial_completion_context.workspace.get_document(
                    doc_uri=uri, accept_from_file=True
                ),
            )

            if doc is None:
                log.debug(
                    "Unable to load document for getting references with uri: %s",
                    uri,
                )
                continue

        if initial_completion_context.doc.uri == doc.uri:
            continue  # Skip (already analyzed).

        new_completion_context = initial_completion_context.create_copy(doc)
        if not is_local_variable:
            # Collect references to global variables as well as named arguments.
            for ref_range in iter_variable_references_in_doc(
                new_completion_context,
                variable_found,
                named_argument_var_references_computer,
            ):
                ret.append({"uri": doc.uri, "range": ref_range})
        else:
            # We still need to collect references to named arguments.
            named_argument_var_references_computer.add_references_to_named_keyword_arguments_from_doc(
                new_completion_context, ret
            )

    return ret.lst


def references_for_keyword_found(
    completion_context: ICompletionContext,
    keyword_found: IKeywordFound,
    include_declaration: bool,
) -> list:
    from robocorp_ls_core import uris
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    ret = _PreventDuplicatesInList()

    normalized_name = normalize_robot_name(keyword_found.keyword_name)
    # Ok, we have the keyword definition, now, we must actually look for the
    # references...
    if include_declaration:
        ret.append(
            {
                "uri": uris.from_fs_path(keyword_found.source),
                "range": {
                    "start": {
                        "line": keyword_found.lineno,
                        "character": keyword_found.col_offset,
                    },
                    "end": {
                        "line": keyword_found.end_lineno,
                        "character": keyword_found.end_col_offset,
                    },
                },
            }
        )

    from robotframework_ls.impl.workspace_symbols import iter_symbols_caches

    for symbols_cache in iter_symbols_caches(
        None, completion_context, force_all_docs_in_workspace=True, timeout=999999
    ):
        completion_context.check_cancelled()
        if symbols_cache.has_keyword_usage(normalized_name):
            doc: Optional[IRobotDocument] = symbols_cache.get_doc()
            if doc is None:
                uri = symbols_cache.get_uri()
                if uri is None:
                    continue

                doc = typing.cast(
                    Optional[IRobotDocument],
                    completion_context.workspace.get_document(
                        doc_uri=uri, accept_from_file=True
                    ),
                )

                if doc is None:
                    log.debug(
                        "Unable to load document for getting references with uri: %s",
                        uri,
                    )
                    continue

            ref_range: RangeTypedDict
            cp = completion_context.create_copy(doc)
            for ref_range in iter_keyword_references_in_doc(
                cp, doc, normalized_name, keyword_found
            ):
                ret.append({"uri": doc.uri, "range": ref_range})

    return ret.lst
