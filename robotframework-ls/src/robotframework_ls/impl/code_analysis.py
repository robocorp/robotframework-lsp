from functools import lru_cache
import re
import sys
from typing import Dict, Optional, List, Tuple

from robocorp_ls_core.lsp import (
    DiagnosticSeverity,
    DiagnosticTag,
    ICustomDiagnosticDataUndefinedKeywordTypedDict,
    ICustomDiagnosticDataUndefinedResourceTypedDict,
    ICustomDiagnosticDataUndefinedVarImportTypedDict,
    ICustomDiagnosticDataUndefinedLibraryTypedDict,
)
from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.ast_utils import MAX_ERRORS
from robotframework_ls.impl.protocols import (
    IKeywordFound,
    IKeywordCollector,
    ICompletionContext,
    ILibraryDoc,
    INode,
    IVariableFound,
    AbstractVariablesCollector,
    VariableKind,
    AbstractKeywordCollector,
)
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_LINT_VARIABLES,
    OPTION_ROBOT_LINT_IGNORE_VARIABLES,
    OPTION_ROBOT_LINT_IGNORE_ENVIRONMENT_VARIABLES,
)
from robotframework_ls.impl.robot_constants import STDLIBS_LOWER
import typing


log = get_logger(__name__)


class _KeywordContainer(object):
    def __init__(self) -> None:
        self._name_to_keywords: Dict[str, List[IKeywordFound]] = {}
        self._names_with_variables: Dict[str, List[IKeywordFound]] = {}

    def add_keyword(self, keyword_found: IKeywordFound) -> None:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        lst = self._name_to_keywords.get(normalized_name)
        if lst is None:
            lst = self._name_to_keywords[normalized_name] = []
        lst.append(keyword_found)

        if "{" in normalized_name:
            lst = self._names_with_variables.get(normalized_name)
            if lst is None:
                lst = self._names_with_variables[normalized_name] = []
            lst.append(keyword_found)

    def get_keywords(self, normalized_keyword_name: str) -> List[IKeywordFound]:
        from robotframework_ls.impl.text_utilities import matches_name_with_variables

        keyword_found = self._name_to_keywords.get(normalized_keyword_name)

        ret = []
        if keyword_found is not None:
            ret.extend(keyword_found)

        # We do not have an exact match, still, we need to check if we may
        # have a match in keywords that accept variables.
        for name, keyword_found in self._names_with_variables.items():
            if matches_name_with_variables(normalized_keyword_name, name):
                ret.extend(keyword_found)

        return ret


class _VariablesCollector(AbstractVariablesCollector):
    def __init__(self, on_unresolved_variable_import):
        self._variables_collected: Dict[str, List[IVariableFound]] = {}
        self._template_variables_collected: List[Tuple[str, IVariableFound]] = []
        self.on_unresolved_variable_import = on_unresolved_variable_import

        self._env_variables_collected: Dict[str, IVariableFound] = {}

    def accepts(self, variable_name: str) -> bool:
        return True

    def on_env_variable(self, variable_found: IVariableFound):
        upper = variable_found.variable_name.upper()
        self._env_variables_collected[upper] = variable_found

    def on_variable(self, variable_found: IVariableFound):
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized = normalize_robot_name(variable_found.variable_name)
        if "{" in normalized:
            self._template_variables_collected.append((normalized, variable_found))

        lst = self._variables_collected.get(normalized)
        if lst is None:
            lst = self._variables_collected[normalized] = []
        lst.append(variable_found)

    def contains_env_variable(self, variable_name_upper: str) -> bool:
        return variable_name_upper in self._env_variables_collected

    def contains_variable(
        self, variable_name: str, var_line: int, var_col_offset: int
    ) -> bool:
        from robotframework_ls.impl.text_utilities import matches_name_with_variables

        variables_found: Optional[List[IVariableFound]] = self._variables_collected.get(
            variable_name
        )
        if variables_found:
            for v in variables_found:
                if v.lineno < var_line:
                    return True

                if (
                    v.lineno == var_line
                    and v.variable_kind == VariableKind.ARGUMENT
                    and v.col_offset < var_col_offset
                ):
                    return True

        for template_var, v in self._template_variables_collected:
            if v.lineno < var_line:
                if matches_name_with_variables(variable_name, template_var):
                    return True

        return False


class _AnalysisKeywordsCollector(object):
    def __init__(
        self,
        on_unresolved_library,
        on_unresolved_resource,
        on_resolved_library,
    ):
        self._keywords_container = _KeywordContainer()
        self._resource_name_to_keywords_container = {}
        self._library_name_to_keywords_container = {}

        self.on_unresolved_library = on_unresolved_library
        self.on_unresolved_resource = on_unresolved_resource
        self.on_resolved_library = on_resolved_library

    def accepts(self, keyword_name):
        return True

    def on_keyword(self, keyword_found: IKeywordFound):
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        # Note: Even if something is imported 'WITH NAME', it's still added
        # to the global scope (there's just an additional reference with the
        # new name).
        self._keywords_container.add_keyword(keyword_found)
        library_name = keyword_found.library_name
        library_alias = keyword_found.library_alias
        resource_name = keyword_found.resource_name

        if library_name:
            if library_alias:
                name = normalize_robot_name(library_alias)
            else:
                name = normalize_robot_name(library_name)
            dct = self._library_name_to_keywords_container
        elif resource_name:
            name = normalize_robot_name(resource_name)
            dct = self._resource_name_to_keywords_container
        else:
            log.info(
                "No library name nor resource name for keyword: %s",
                keyword_found.keyword_name,
            )
            return

        keyword_container = dct.get(name)
        if keyword_container is None:
            keyword_container = dct[name] = _KeywordContainer()

        keyword_container.add_keyword(keyword_found)

    def get_keywords(self, normalized_keyword_name: str) -> List[IKeywordFound]:
        from robotframework_ls.impl import text_utilities

        ret = []

        # Note: the name could be something as `alias.keywordname` or
        # 'libraryname.keywordname`. In this case, we need to verify if there's
        # a library/alias with that specific name.
        for name, remainder in text_utilities.iter_dotted_names(
            normalized_keyword_name
        ):
            if not name or not remainder:
                continue
            containers = []
            keywords_container = self._resource_name_to_keywords_container.get(name)
            if keywords_container:
                containers.append(keywords_container)
            keywords_container = self._library_name_to_keywords_container.get(name)
            if keywords_container:
                containers.append(keywords_container)

            for keywords_container in containers:
                ret.extend(keywords_container.get_keywords(remainder))

        if not ret:
            # Finding with a dotted name has higher priority over finding it
            # without the qualifier.
            ret.extend(self._keywords_container.get_keywords(normalized_keyword_name))

        return ret

    def __typecheckself__(self) -> None:
        _: IKeywordCollector = check_implements(self)


def collect_analysis_errors(initial_completion_context):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_error_from_node
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl.text_utilities import normalize_robot_name
    from robotframework_ls.impl.text_utilities import contains_variable_text
    from robotframework_ls.impl.keyword_argument_analysis import (
        UsageInfoForKeywordArgumentAnalysis,
    )
    from robot.api import Token

    errors = []
    config = initial_completion_context.config

    def on_resolved_library(
        completion_context: ICompletionContext,
        library_node: Optional[INode],
        library_doc: ILibraryDoc,
    ):
        if library_node is None:
            return

        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_KEYWORD_CALL_ARGUMENTS,
        )

        if config is not None and not config.get_setting(
            OPTION_ROBOT_LINT_KEYWORD_CALL_ARGUMENTS, bool, True
        ):
            return

        doc = completion_context.doc
        if not doc or doc.uri != initial_completion_context.doc.uri:
            return

        from robotframework_ls.impl.keyword_argument_analysis import (
            KeywordArgumentAnalysis,
        )

        library_args = []
        if library_doc.inits:
            keyword_doc = library_doc.inits[0]
            library_args = keyword_doc.args

        # Ok, we found the keyword, let's check if the arguments are correct.
        keyword_argument_analysis = KeywordArgumentAnalysis(library_args)

        name_token = library_node.get_token(Token.NAME)
        if name_token is not None:
            for error in keyword_argument_analysis.collect_keyword_usage_errors(
                UsageInfoForKeywordArgumentAnalysis(library_node, name_token)
            ):
                errors.append(error)

    def on_unresolved_library(
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_UNDEFINED_LIBRARIES,
        )
        from robotframework_ls.impl.robot_version import get_robot_major_version

        if config is not None and not config.get_setting(
            OPTION_ROBOT_LINT_UNDEFINED_LIBRARIES, bool, True
        ):
            return

        doc = completion_context.doc
        if doc and doc.uri == initial_completion_context.doc.uri:
            start = (lineno - 1, col_offset)
            end = (end_lineno - 1, end_col_offset)

            additional = ""
            if error_msg is None:
                error_msg = ""
            else:
                if "expected" in error_msg:
                    if re.search(r"expected\s+(.*)\s+argument(s)?,\s+got", error_msg):
                        additional = f'\nConsider using default arguments in the {library_name} constructor and\ncalling the "Robot Framework: Clear caches and restart" action or\nadding "{library_name}" to the "robot.libraries.libdoc.needsArgs"\nsetting to pass the typed arguments when generating the libspec.'

                if not additional and "Importing" in error_msg:
                    if get_robot_major_version() <= 3:
                        pattern = r"Importing\s+test\s+library(.*)failed"
                    else:
                        pattern = r"Importing\s+library(.*)failed"
                    if re.search(pattern, error_msg):
                        additional = f'\nConsider adding the needed paths to the "robot.pythonpath" setting\nand calling the "Robot Framework: Clear caches and restart" action.'

                    if "{" in library_name and resolved_name:
                        error_msg += f"\nNote: resolved name: {resolved_name}"

            error = ast_utils.Error(
                f"Unresolved library: {library_name}.{error_msg}{additional}".strip(),
                start,
                end,
            )
            undefined_var_import_data: ICustomDiagnosticDataUndefinedLibraryTypedDict = {
                "kind": "undefined_library",
                "name": library_name,
                "resolved_name": resolved_name,
            }
            error.data = undefined_var_import_data

            errors.append(error)

    def on_unresolved_resource(
        completion_context: ICompletionContext,
        resource_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_UNDEFINED_RESOURCES,
        )

        if config is not None and not config.get_setting(
            OPTION_ROBOT_LINT_UNDEFINED_RESOURCES, bool, True
        ):
            return

        doc = completion_context.doc
        if doc and doc.uri == initial_completion_context.doc.uri:
            start = (lineno - 1, col_offset)
            end = (end_lineno - 1, end_col_offset)
            if not error_msg:
                error_msg = f"Unresolved resource: {resource_name}"
                if "{" in resource_name and resolved_name:
                    error_msg += f"\nNote: resolved name: {resolved_name}"

            error = ast_utils.Error(error_msg, start, end)
            undefined_resource_data: ICustomDiagnosticDataUndefinedResourceTypedDict = {
                "kind": "undefined_resource",
                "name": resource_name,
                "resolved_name": resolved_name,
            }
            error.data = undefined_resource_data
            errors.append(error)

    collector = _AnalysisKeywordsCollector(
        on_unresolved_library,
        on_unresolved_resource,
        on_resolved_library,
    )
    collect_keywords(initial_completion_context, collector)

    ast = initial_completion_context.get_ast()
    for keyword_usage_info in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        initial_completion_context.check_cancelled()
        if contains_variable_text(keyword_usage_info.name):
            continue
        normalized_name = normalize_robot_name(keyword_usage_info.name)
        keywords_found = collector.get_keywords(normalized_name)
        if not keywords_found and keyword_usage_info.prefix:
            keywords_found = collector.get_keywords(
                normalize_robot_name(keyword_usage_info.prefix + normalized_name)
            )

        try:
            if not keywords_found:
                from robotframework_ls.impl.robot_lsp_constants import (
                    OPTION_ROBOT_LINT_UNDEFINED_KEYWORDS,
                )

                if config is not None and not config.get_setting(
                    OPTION_ROBOT_LINT_UNDEFINED_KEYWORDS, bool, True
                ):
                    continue

                node = keyword_usage_info.node
                error = create_error_from_node(
                    node,
                    "Undefined keyword: %s." % (keyword_usage_info.name,),
                    tokens=[keyword_usage_info.token],
                )
                undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict = {
                    "kind": "undefined_keyword",
                    "name": keyword_usage_info.name,
                }
                error.data = undefined_keyword_data
                errors.append(error)

            else:
                new_keywords_found: List[IKeywordFound] = []
                if len(keywords_found) > 1:
                    # We still can't be sure, it's possible that we found the
                    # same keyword multiple times. Let's check where they're found.
                    node = keyword_usage_info.node
                    found_in = set()
                    count_not_in_stdlib = 0
                    found_in_current = False

                    for keyword_found in keywords_found:
                        if (
                            keyword_found.source
                            == initial_completion_context.original_doc.path
                        ):
                            found_in_current = True
                            for keyword_found in keywords_found:
                                # If it's defined in the current file,
                                # it overrides any other scope.
                                new_keywords_found = [
                                    k
                                    for k in keywords_found
                                    if k.source
                                    == initial_completion_context.original_doc.path
                                ]
                                for k in new_keywords_found:
                                    library_name = k.library_name
                                    library_alias = k.library_alias
                                    if library_alias:
                                        found_in.add(library_alias)
                                    else:
                                        if library_name:
                                            found_in.add(library_name)
                                        else:
                                            resource_name = keyword_found.resource_name
                                            found_in.add(resource_name)
                                count_not_in_stdlib = len(new_keywords_found)
                            break

                        library_name = keyword_found.library_name
                        if (
                            not library_name
                            or library_name.lower() not in STDLIBS_LOWER
                        ):
                            count_not_in_stdlib += 1
                            # A builtin lib is always overridden by any other place,
                            # so, don't add it to the new_keywords_found unless
                            # it was found in a non-stdlib library/resource.
                            new_keywords_found.append(keyword_found)

                        library_alias = keyword_found.library_alias
                        if library_alias:
                            found_in.add(library_alias)
                        else:
                            if library_name:
                                found_in.add(library_name)
                            else:
                                resource_name = keyword_found.resource_name
                                found_in.add(resource_name)

                    if count_not_in_stdlib > 1:
                        if found_in_current:
                            msg = f"Multiple keywords matching: '{keyword_usage_info.name}' in current file."
                        else:

                            found_in_str = "'" + "', '".join(sorted(found_in)) + "'"
                            if len(found_in) == 1:
                                msg = f"Multiple keywords matching: '{keyword_usage_info.name}' in {found_in_str}."
                            else:
                                if "." in keyword_usage_info.name:
                                    msg = f"Multiple keywords matching: '{keyword_usage_info.name}' in {found_in_str}."
                                else:
                                    msg = (
                                        f"Multiple keywords matching: '{keyword_usage_info.name}' in {found_in_str}.\n"
                                        f"Please provide the name with the full qualifier (i.e.: "
                                        f"'{sorted(found_in)[0] + '.' + keyword_usage_info.name}')."
                                    )
                        from robotframework_ls.impl.robot_lsp_constants import (
                            OPTION_ROBOT_LINT_KEYWORD_RESOLVES_TO_MULTIPLE_KEYWORDS,
                        )

                        if config is None or config.get_setting(
                            OPTION_ROBOT_LINT_KEYWORD_RESOLVES_TO_MULTIPLE_KEYWORDS,
                            bool,
                            True,
                        ):
                            error = create_error_from_node(
                                node,
                                msg,
                                tokens=[keyword_usage_info.token],
                            )
                            errors.append(error)

                from robotframework_ls.impl.robot_lsp_constants import (
                    OPTION_ROBOT_LINT_KEYWORD_CALL_ARGUMENTS,
                )

                if config is not None and not config.get_setting(
                    OPTION_ROBOT_LINT_KEYWORD_CALL_ARGUMENTS, bool, True
                ):
                    continue

                from robotframework_ls.impl.keyword_argument_analysis import (
                    KeywordArgumentAnalysis,
                )

                if new_keywords_found:
                    keywords_found = new_keywords_found

                # Still do the keyword analysis even if multiple keywords match
                # See: https://github.com/robocorp/robotframework-lsp/issues/724
                found_error_in_arg_analysis = False
                for keyword_found in keywords_found:
                    if found_error_in_arg_analysis:
                        break

                    keyword_token = keyword_usage_info.node.get_token(Token.KEYWORD)
                    if keyword_token is not None:
                        # Ok, we found the keyword, let's check if the arguments are correct.
                        keyword_argument_analysis = KeywordArgumentAnalysis(
                            keyword_found.keyword_args, keyword_found
                        )

                        for (
                            error
                        ) in keyword_argument_analysis.collect_keyword_usage_errors(
                            UsageInfoForKeywordArgumentAnalysis(
                                keyword_usage_info.node,
                                keyword_token,
                            )
                        ):
                            errors.append(error)
                            found_error_in_arg_analysis = True
                    else:
                        # Not a keyword usage, check for other cases (template/fixtures).
                        if keyword_usage_info.node.type in (
                            Token.TEMPLATE,
                            Token.TEST_TEMPLATE,
                        ):
                            # For templates the arguments are actually gotten from the test.
                            stack = keyword_usage_info.stack
                            if keyword_usage_info.node.type == Token.TEST_TEMPLATE:
                                stack = [ast]
                            for (
                                template_arguments_node_info
                            ) in ast_utils.iter_arguments_from_template(
                                stack, keyword_usage_info.node
                            ):
                                keyword_argument_analysis = KeywordArgumentAnalysis(
                                    keyword_found.keyword_args, keyword_found
                                )
                                args_tokens = template_arguments_node_info.node.tokens
                                for (
                                    error
                                ) in keyword_argument_analysis.collect_keyword_usage_errors(
                                    UsageInfoForKeywordArgumentAnalysis(
                                        template_arguments_node_info.node,
                                        args_tokens[-1],
                                        args_tokens,
                                    )
                                ):
                                    errors.append(error)
                                    found_error_in_arg_analysis = True

                for keyword_found in keywords_found:
                    if keyword_found.is_deprecated():
                        error = create_error_from_node(
                            keyword_usage_info.node,
                            f"Keyword: {keyword_usage_info.name} is deprecated",
                            tokens=[keyword_usage_info.token],
                        )
                        error.severity = DiagnosticSeverity.Hint
                        error.tags = [DiagnosticTag.Deprecated]
                        errors.append(error)
                        break

            if len(errors) >= MAX_ERRORS:
                # i.e.: Collect at most 100 errors
                break
        except:
            log.exception("Exception collecting errors")

    if len(errors) >= MAX_ERRORS:
        return errors

    for error in _collect_undefined_variables_errors(initial_completion_context):
        errors.append(error)
        if len(errors) >= MAX_ERRORS:
            # i.e.: Collect at most 100 errors
            break

    if len(errors) >= MAX_ERRORS:
        return errors

    _collect_unused_keyword_errors(initial_completion_context, errors)

    return errors


class _NoReferencesErrorsKeywordsCollector(AbstractKeywordCollector):
    def __init__(self, errors):
        from robocorp_ls_core.lsp import Error

        self.errors: List[Error] = errors

    def accepts(self, keyword_name: str) -> bool:
        return True

    def on_keyword(self, keyword_found: IKeywordFound):
        from robocorp_ls_core.lsp import Error

        if len(self.errors) >= MAX_ERRORS:
            # i.e.: Collect at most 100 errors
            return

        from robotframework_ls.impl.references import references_for_keyword_found

        completion_context = keyword_found.completion_context
        assert completion_context
        references = references_for_keyword_found(
            completion_context, keyword_found, include_declaration=False
        )
        if not references:
            start = (keyword_found.lineno, keyword_found.col_offset)
            end = (keyword_found.end_lineno, keyword_found.end_col_offset)

            error = Error(
                f"The keyword: '{keyword_found.keyword_name}' is not used in the workspace.",
                start,
                end,
                DiagnosticSeverity.Warning,
            )
            self.errors.append(error)


def _collect_unused_keyword_errors(completion_context: ICompletionContext, errors):
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )
    from robotframework_ls.impl.robot_workspace import RobotWorkspace

    config = completion_context.config

    if config is not None and config.get_setting(
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
        bool,
        False,
    ):

        from robotframework_ls.impl.collect_keywords import collect_keywords_from_ast

        # The lint process usually does not have workspace indexing turned on,
        # but it's needed for finding unused references, so, turn it on now.

        workspace: Optional[RobotWorkspace] = typing.cast(
            Optional[RobotWorkspace], completion_context.workspace
        )
        if not workspace:
            log.critical("Not analyzing unused keywords because workspace is None.")
            return

        workspace_indexer = workspace.workspace_indexer
        if workspace_indexer is None:
            workspace.setup_workspace_indexer()
            workspace_indexer = workspace.workspace_indexer
            assert workspace_indexer is not None

        ast = completion_context.get_ast()
        collector = _NoReferencesErrorsKeywordsCollector(errors)
        collect_keywords_from_ast(ast, completion_context, collector)


@lru_cache(maxsize=1000)
def _skip_variable_analysis(normalized_variable_name):
    from robotframework_ls.impl.variable_resolve import is_number_var
    from robotframework_ls.impl.variable_resolve import is_python_eval_var

    if is_number_var(normalized_variable_name):
        return True

    if is_python_eval_var(normalized_variable_name):
        return True

    return False


def _env_vars_upper():
    import os

    return tuple(x.upper() for x in os.environ)


def _collect_undefined_variables_errors(initial_completion_context):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.variable_resolve import normalize_variable_name
    from robotframework_ls.impl.ast_utils import create_error_from_node
    from robotframework_ls.impl.variable_resolve import robot_search_variable

    config = initial_completion_context.config
    if config is not None and not config.get_setting(
        OPTION_ROBOT_LINT_VARIABLES, bool, True
    ):
        return

    unresolved_variable_import_errors = []

    def on_unresolved_variable_import(
        completion_context: ICompletionContext,
        variable_import_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
        resolved_name: str,
    ):
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_UNDEFINED_VARIABLE_IMPORTS,
        )

        if config is not None and not config.get_setting(
            OPTION_ROBOT_LINT_UNDEFINED_VARIABLE_IMPORTS, bool, True
        ):
            return

        doc = completion_context.doc
        if doc and doc.uri == initial_completion_context.doc.uri:
            start = (lineno - 1, col_offset)
            end = (end_lineno - 1, end_col_offset)
            if not error_msg:
                error_msg = f"Unresolved variable import: {variable_import_name}"
                if "{" in variable_import_name and resolved_name:
                    error_msg += f"\nNote: resolved name: {resolved_name}"

            error = ast_utils.Error(error_msg, start, end)
            undefined_var_import_data: ICustomDiagnosticDataUndefinedVarImportTypedDict = {
                "kind": "undefined_var_import",
                "name": variable_import_name,
                "resolved_name": resolved_name,
            }
            error.data = undefined_var_import_data
            unresolved_variable_import_errors.append(error)

    from robotframework_ls.impl import variable_completions

    ignore_variables = set()
    if config is not None:
        ignore_variables.update(
            normalize_variable_name(str(x))
            for x in config.get_setting(OPTION_ROBOT_LINT_IGNORE_VARIABLES, list, [])
        )

    ignore_environment_variables = set()
    if config is not None:
        ignore_environment_variables.update(
            str(x).upper()
            for x in config.get_setting(
                OPTION_ROBOT_LINT_IGNORE_ENVIRONMENT_VARIABLES, list, []
            )
        )

    ast = initial_completion_context.get_ast()

    globals_collector = _VariablesCollector(
        on_unresolved_variable_import=on_unresolved_variable_import
    )

    # Collect undefined variables
    variable_completions.collect_global_variables(
        initial_completion_context, globals_collector, only_current_doc=False
    )

    yield from iter(unresolved_variable_import_errors)

    env_vars_upper = None

    for token_info in ast_utils.iter_variable_references(ast):

        initial_completion_context.check_cancelled()

        if token_info.node.__class__.__name__ in (
            "ResourceImport",
            "LibraryImport",
            "VariableImport",
        ):
            # These ones are handled differently as it ends up in an unresolved
            # import.
            continue

        if (
            token_info.node.__class__.__name__ == "KeywordCall"
            and token_info.node.keyword == "Comment"
        ):
            # Special handling for 'Comment' keyword (variables are not
            # resolved when calling the 'Comment' keyword).
            # https://github.com/robocorp/robotframework-lsp/issues/665
            continue

        var_name = token_info.token.value
        var_line = token_info.token.lineno - 1  # We want it 0-based
        var_col_offset = token_info.token.col_offset

        if token_info.var_info.var_identifier == "%":

            if "=" in var_name + token_info.var_info.extended_part:
                # Consider case: %{SOME_VAR=}
                # Consider case: %{SOME_VAR=default val}
                continue

            var_name_upper = var_name.upper()
            if var_name_upper in ignore_environment_variables:
                continue

            if env_vars_upper is None:
                env_vars_upper = _env_vars_upper()

            if (
                var_name_upper not in env_vars_upper
                and not globals_collector.contains_env_variable(var_name_upper)
            ):
                # Environment variable
                yield create_error_from_node(
                    token_info.node,
                    f"Undefined environment variable: {token_info.token.value}",
                    tokens=[token_info.token],
                )
            continue

        check_names = [normalize_variable_name(var_name)]
        if token_info.var_info.extended_part.strip():

            robot_match_in_ext = robot_search_variable(
                token_info.var_info.extended_part
            )
            if robot_match_in_ext is not None and robot_match_in_ext.base:
                continue

            check_names.append(
                normalize_variable_name(var_name + token_info.var_info.extended_part)
            )

        locals_collector = None

        found = False
        for normalized_variable_name in check_names:
            if normalized_variable_name in ignore_variables:
                found = True
                break

            if _skip_variable_analysis(normalized_variable_name):
                found = True
                break

            if globals_collector.contains_variable(
                normalized_variable_name, sys.maxsize, 0
            ):
                found = True
                break

            if locals_collector is None:
                locals_collector = _VariablesCollector(lambda *args, **kwargs: None)
                local_ctx = initial_completion_context.create_copy_with_selection(
                    line=token_info.token.lineno - 1,
                    col=token_info.token.col_offset,
                )

                variable_completions.collect_local_variables(
                    local_ctx, locals_collector, token_info
                )

            if locals_collector.contains_variable(
                normalized_variable_name, var_line, var_col_offset
            ):
                found = True
                break

        if not found:
            yield create_error_from_node(
                token_info.node,
                f"Undefined variable: {token_info.token.value}",
                tokens=[token_info.token],
            )
