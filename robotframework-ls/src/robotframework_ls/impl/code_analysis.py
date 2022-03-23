from typing import Dict, Optional
import re

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
)
from robocorp_ls_core.lsp import DiagnosticSeverity, DiagnosticTag
from robotframework_ls.impl.robot_lsp_constants import (
    OPTION_ROBOT_LINT_VARIABLES,
    OPTION_ROBOT_LINT_IGNORE_VARIABLES,
)
from functools import lru_cache


log = get_logger(__name__)


class _KeywordContainer(object):
    def __init__(self) -> None:
        self._name_to_keyword: Dict[str, IKeywordFound] = {}
        self._names_with_variables: Dict[str, IKeywordFound] = {}

    def add_keyword(self, keyword_found: IKeywordFound) -> None:
        from robotframework_ls.impl.text_utilities import normalize_robot_name

        normalized_name = normalize_robot_name(keyword_found.keyword_name)
        self._name_to_keyword[normalized_name] = keyword_found

        if "{" in normalized_name:
            self._names_with_variables[normalized_name] = keyword_found

    def get_keyword(self, normalized_keyword_name: str) -> Optional[IKeywordFound]:
        from robotframework_ls.impl.text_utilities import matches_robot_keyword

        keyword_found = self._name_to_keyword.get(normalized_keyword_name)

        if keyword_found is not None:
            return keyword_found

        # We do not have an exact match, still, we need to check if we may
        # have a match in keywords that accept variables.
        for name, keyword_found in self._names_with_variables.items():
            if matches_robot_keyword(normalized_keyword_name, name):
                return keyword_found

        return None


class _VariablesCollector(object):
    def __init__(self, on_unresolved_variable_import):
        self._variables_collected = set()
        self.on_unresolved_variable_import = on_unresolved_variable_import

    def accepts(self, variable_name: str) -> bool:
        from robotframework_ls.impl.variable_resolve import normalize_variable_name

        self._variables_collected.add(normalize_variable_name(variable_name))
        # We don't want to create the IVariableFound, just the names should be
        # enough for our usage.
        return False

    def on_variable(self, variable_found: IVariableFound):
        pass

    def contains_variable(self, variable_name):
        return variable_name in self._variables_collected


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

    def get_keyword(self, normalized_keyword_name: str) -> Optional[IKeywordFound]:
        from robotframework_ls.impl import text_utilities

        keyword_found = self._keywords_container.get_keyword(normalized_keyword_name)
        if keyword_found is not None:
            return keyword_found

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
                keyword_found = keywords_container.get_keyword(remainder)
                if keyword_found is not None:
                    return keyword_found

        return None

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

            errors.append(
                ast_utils.Error(
                    f"Unresolved library: {library_name}.{error_msg}{additional}".strip(),
                    start,
                    end,
                )
            )

    def on_unresolved_resource(
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
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
                error_msg = f"Unresolved resource: {library_name}"

            errors.append(ast_utils.Error(error_msg, start, end))

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
        keyword_found = collector.get_keyword(normalized_name)
        try:
            if not keyword_found:
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
                errors.append(error)

            else:
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

                # Ok, we found the keyword, let's check if the arguments are correct.
                keyword_argument_analysis = KeywordArgumentAnalysis(
                    keyword_found.keyword_args
                )

                keyword_token = None
                if keyword_token is None:
                    keyword_token = keyword_usage_info.node.get_token(Token.KEYWORD)

                if keyword_token is not None:
                    for error in keyword_argument_analysis.collect_keyword_usage_errors(
                        UsageInfoForKeywordArgumentAnalysis(
                            keyword_usage_info.node,
                            keyword_token,
                        )
                    ):
                        errors.append(error)

                if keyword_found.is_deprecated():
                    error = create_error_from_node(
                        keyword_usage_info.node,
                        f"Keyword: {keyword_usage_info.name} is deprecated",
                        tokens=[keyword_usage_info.token],
                    )
                    error.severity = DiagnosticSeverity.Hint
                    error.tags = [DiagnosticTag.Deprecated]
                    errors.append(error)

            if len(errors) >= MAX_ERRORS:
                # i.e.: Collect at most 100 errors
                break
        except:
            log.exception("Error collecting exceptions")

    for error in _collect_undefined_variables_errors(initial_completion_context):
        errors.append(error)
        if len(errors) >= MAX_ERRORS:
            # i.e.: Collect at most 100 errors
            break

    return errors


def _is_number_var(normalized_variable_name):
    # see: robot.variables.finders.NumberFinder
    try:
        bases = {"0b": 2, "0o": 8, "0x": 16}
        if normalized_variable_name.startswith(tuple(bases)):
            return int(
                normalized_variable_name[2:], bases[normalized_variable_name[:2]]
            )
        int(normalized_variable_name)
        return True
    except:
        pass  # Let's try float...

    try:
        float(normalized_variable_name)
        return True
    except:
        pass

    return False


def _is_python_eval_var(normalized_variable_name):
    return (
        len(normalized_variable_name) >= 2
        and normalized_variable_name[0] == "{"
        and normalized_variable_name[-1] == "}"
    )


@lru_cache(maxsize=1000)
def _skip_variable_analysis(normalized_variable_name):

    if _is_number_var(normalized_variable_name):
        return True

    if _is_python_eval_var(normalized_variable_name):
        return True

    return False


_match_extended = re.compile(
    r"""
    (.+?)          # base name (group 1)
    ([^\s\w].+)    # extended part (group 2)
""",
    re.UNICODE | re.VERBOSE,
).match


def _extract_base_from_extended_var_name(normalized_variable_name):
    m = _match_extended(normalized_variable_name)
    if m is None:
        return normalized_variable_name

    base_name, _extended = m.groups()
    return base_name


def _env_vars_upper():
    import os

    return tuple(x.upper() for x in os.environ)


def _collect_undefined_variables_errors(initial_completion_context):
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.variable_resolve import normalize_variable_name
    from robotframework_ls.impl.ast_utils import create_error_from_node

    config = initial_completion_context.config
    if config is not None and not config.get_setting(
        OPTION_ROBOT_LINT_VARIABLES, bool, True
    ):
        return

    unresolved_variable_import_errors = []

    def on_unresolved_variable_import(
        completion_context: ICompletionContext,
        library_name: str,
        lineno: int,
        end_lineno: int,
        col_offset: int,
        end_col_offset: int,
        error_msg: Optional[str],
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
                error_msg = f"Unresolved variable import: {library_name}"

            unresolved_variable_import_errors.append(
                ast_utils.Error(error_msg, start, end)
            )

    from robotframework_ls.impl import variable_completions

    ignore_variables = set()
    if config is not None:
        ignore_variables.update(
            normalize_variable_name(str(x))
            for x in config.get_setting(OPTION_ROBOT_LINT_IGNORE_VARIABLES, list, [])
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

        var_name = token_info.token.value
        if token_info.var_identifier == "%":
            from robotframework_ls.impl.variable_resolve import extract_variable_base

            if env_vars_upper is None:
                env_vars_upper = _env_vars_upper()

            if extract_variable_base(var_name).upper() not in env_vars_upper:
                # Environment variable
                yield create_error_from_node(
                    token_info.node,
                    f"Undefined environment variable: {token_info.token.value}",
                    tokens=[token_info.token],
                )
            continue

        normalized_variable_name = normalize_variable_name(var_name)

        found = False
        while not found:
            if normalized_variable_name in ignore_variables:
                found = True
                break

            if _skip_variable_analysis(normalized_variable_name):
                found = True
                break

            if globals_collector.contains_variable(normalized_variable_name):
                found = True
                break

            locals_collector = _VariablesCollector(lambda *args, **kwargs: None)
            local_ctx = initial_completion_context.create_copy_with_selection(
                line=token_info.token.lineno - 1,
                col=token_info.token.col_offset - 1,
            )

            variable_completions.collect_local_variables(
                local_ctx, locals_collector, token_info
            )
            if locals_collector.contains_variable(normalized_variable_name):
                found = True
                break

            extracted_base = _extract_base_from_extended_var_name(
                normalized_variable_name
            )
            if extracted_base and extracted_base != normalized_variable_name:
                normalized_variable_name = extracted_base
            else:
                break

        if not found:
            yield create_error_from_node(
                token_info.node,
                f"Undefined variable: {token_info.token.value}",
                tokens=[token_info.token],
            )
