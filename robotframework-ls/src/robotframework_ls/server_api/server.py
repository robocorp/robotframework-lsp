from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.basic import overrides
from robocorp_ls_core.robotframework_log import get_logger, get_log_level
from typing import Optional, List, Dict, Deque, Tuple, Sequence
from robocorp_ls_core.protocols import (
    IConfig,
    IMonitor,
    ITestInfoTypedDict,
    IWorkspace,
    ActionResultDict,
)
from functools import partial
from robocorp_ls_core.jsonrpc.endpoint import require_monitor
from robocorp_ls_core.lsp import (
    SymbolInformationTypedDict,
    FoldingRangeTypedDict,
    HoverTypedDict,
    TextDocumentTypedDict,
    CodeLensTypedDict,
    DocumentSymbolTypedDict,
    PositionTypedDict,
    LocationTypedDict,
    DocumentHighlightTypedDict,
    RangeTypedDict,
    CompletionItemTypedDict,
    WorkspaceEditTypedDict,
    SelectionRangeTypedDict,
    TextDocumentCodeActionTypedDict,
    ICustomDiagnosticDataTypedDict,
    CommandTypedDict,
)
from robotframework_ls.impl.protocols import (
    IKeywordFound,
    IDefinition,
    ICompletionContext,
    EvaluatableExpressionTypedDict,
    IVariablesFromArgumentsFileLoader,
)
from robocorp_ls_core.watchdog_wrapper import IFSObserver
import itertools
import typing
import sys
import threading
from robocorp_ls_core.jsonrpc.exceptions import JsonRpcException
import os
from robocorp_ls_core import uris


log = get_logger(__name__)


def complete_all(
    completion_context: ICompletionContext,
) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl import section_name_completions
    from robotframework_ls.impl import keyword_completions
    from robotframework_ls.impl import variable_completions
    from robotframework_ls.impl import dictionary_completions
    from robotframework_ls.impl import filesystem_section_completions
    from robotframework_ls.impl import keyword_parameter_completions
    from robotframework_ls.impl import auto_import_completions
    from robotframework_ls.impl import library_names_completions
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robotframework_ls.impl import ast_utils

    ret = section_name_completions.complete(completion_context)
    if not ret:
        ret.extend(filesystem_section_completions.complete(completion_context))

    if not ret:
        token_info = completion_context.get_current_token()
        if token_info is not None:
            token = ast_utils.get_keyword_name_token(
                token_info.stack, token_info.node, token_info.token
            )
            if token is not None:
                keyword_name_to_keyword_found: Dict[
                    str, List[IKeywordFound]
                ] = collect_keyword_name_to_keyword_found(completion_context)
                ret.extend(keyword_completions.complete(completion_context))
                ret.extend(
                    auto_import_completions.complete(
                        completion_context, keyword_name_to_keyword_found
                    )
                )
                ret.extend(library_names_completions.complete(completion_context))
                return ret

    if not ret:
        ret.extend(variable_completions.complete(completion_context))

    if not ret:
        ret.extend(dictionary_completions.complete(completion_context))

    if not ret:
        ret.extend(keyword_parameter_completions.complete(completion_context))

    return ret


class RobotFrameworkServerApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(
        self,
        read_from,
        write_to,
        libspec_manager=None,
        observer: Optional[IFSObserver] = None,
        pre_generate_libspecs: bool = False,
        index_workspace: bool = False,
        collect_tests: bool = False,
    ):
        from robotframework_ls.impl.libspec_manager import LibspecManager

        PythonLanguageServer.__init__(self, read_from, write_to)
        self._index_workspace = index_workspace
        self._collect_tests = collect_tests

        if libspec_manager is None:
            try:
                libspec_manager = LibspecManager(
                    observer=observer,
                    endpoint=self._endpoint,
                    pre_generate_libspecs=pre_generate_libspecs,
                )
            except:
                log.exception("Unable to properly initialize the LibspecManager.")
                raise

        self.libspec_manager = libspec_manager
        self._version: Optional[str] = None
        self._logged_version_error = False
        self._next_time = partial(next, itertools.count(0))
        from collections import deque

        self._completion_contexts_saved_lock = threading.Lock()
        self._completion_contexts_saved: Deque[ICompletionContext] = deque()
        self._variables_from_arguments_files_loader: Sequence[
            IVariablesFromArgumentsFileLoader
        ] = []

    @overrides(PythonLanguageServer._create_config)
    def _create_config(self) -> IConfig:
        from robotframework_ls.robot_config import RobotConfig

        return RobotConfig()

    def m_version(self) -> str:
        """
        Kind of a code-smell:

        Either a string with the version is provided or an error message.

        It's now part of the API, so, keep as is.
        """
        if self._version is not None:
            return self._version
        try:
            import robot  # noqa
        except:
            version = (
                'Error in "import robot".\n'
                f"It seems that Robot Framework is not installed in {sys.executable}.\n"
                "Please install it in your environment and restart the Robot Framework Language Server\n"
                'or set: "robot.language-server.python" or "robot.python.executable"\n'
                "to point to a python installation that has Robot Framework installed.\n"
                "Hint: with pip it can be installed with:\n"
                f"{sys.executable} -m pip install robotframework\n"
            )
            log.exception(version)
        else:
            try:
                from robot import get_version

                version = get_version(naked=True)
            except:
                version = (
                    'Error calling "robot.get_version()".\n'
                    f"If the module: {robot}\n"
                    "is a module from your project, please rename it (as it is shadowing the Robot Framework `robot` package)\n"
                    "and restart the Robot Framework Language Server."
                )
                log.exception(version)
        self._version = version
        return self._version

    def _compute_min_version_error(self, min_version: Tuple[int, int]) -> Optional[str]:
        from robocorp_ls_core.basic import check_min_version

        v_or_error = self.m_version()
        try:
            # Check if it's an error or a valid version.
            tuple(int(x) for x in v_or_error.split("."))
        except:
            return v_or_error  # This is an error message

        if not check_min_version(v_or_error, min_version):
            return f"Expected Robot Framework version: {'.'.join((str(x) for x in min_version))}. Found: {v_or_error}"
        return None

    def _check_and_log_rf_dependency_version(self):
        error = self._compute_min_version_error((3, 2))
        if error is not None:
            if self._logged_version_error:
                log.info(
                    "Problem with `robotframework` dependency. See previous errors."
                )
            else:
                log.info(error)
                self._logged_version_error = True
            return False
        return True

    @overrides(PythonLanguageServer.m_workspace__did_change_configuration)
    def m_workspace__did_change_configuration(self, **kwargs):
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE,
        )
        from robotframework_ls.impl import robot_localization

        PythonLanguageServer.m_workspace__did_change_configuration(self, **kwargs)
        self.libspec_manager.config = self.config

        robot_localization.set_global_from_config(self.config)

        try:
            variables_from_arguments_files = self.config.get_setting(
                OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE, str, ""
            ).strip()
            if not variables_from_arguments_files:
                log.debug(
                    "%s not specified", OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE
                )
                self._variables_from_arguments_files_loader = []

            else:
                from robotframework_ls.impl.variables_from_arguments_file import (
                    VariablesFromArgumentsFileLoader,
                )

                created_variables_from_arguments_files = []

                for v in variables_from_arguments_files.split(","):
                    v = v.strip()
                    if not v:
                        continue
                    created_variables_from_arguments_files.append(
                        VariablesFromArgumentsFileLoader(v)
                    )
                created_variables_from_arguments_files = tuple(
                    created_variables_from_arguments_files
                )
                self._variables_from_arguments_files_loader = (
                    created_variables_from_arguments_files
                )

                log.debug(
                    "%s loaders: %s",
                    OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE,
                    created_variables_from_arguments_files,
                )
        except:
            log.exception(
                f"Error getting options: {OPTION_ROBOT_VARIABLES_LOAD_FROM_ARGUMENTS_FILE}"
            )

    @overrides(PythonLanguageServer.lint)
    def lint(self, *args, **kwargs):
        pass  # No-op for this server.

    @overrides(PythonLanguageServer.cancel_lint)
    def cancel_lint(self, *args, **kwargs):
        pass  # No-op for this server.

    @overrides(PythonLanguageServer._obtain_fs_observer)
    def _obtain_fs_observer(self) -> IFSObserver:
        return self.libspec_manager.fs_observer

    @overrides(PythonLanguageServer._create_workspace)
    def _create_workspace(
        self, root_uri: str, fs_observer: IFSObserver, workspace_folders
    ) -> IWorkspace:
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        # Note: note done because our caches are removed promptly
        # for this to work it should be invalidate but the info
        # should be kept around so that we lint dependencies always
        # not just on the first cache invalidation.
        # WIP: test_dependency_graph_integration_lint
        # weak_self = weakref.ref(self)
        #
        # def on_dependency_changed(uri):
        #     s = weak_self()
        #     if s is not None:
        #         endpoint = s._endpoint
        #         if endpoint:
        #             endpoint.notify(
        #                 "$/dependencyChanged",
        #                 {"uri": uri},
        #             )

        robot_workspace = RobotWorkspace(
            root_uri,
            fs_observer,
            workspace_folders,
            libspec_manager=self.libspec_manager,
            index_workspace=self._index_workspace,
            collect_tests=self._collect_tests,
            endpoint=self._endpoint,
        )

        return robot_workspace

    def m_lint(self, doc_uri):
        error = self._compute_min_version_error((3, 2))
        if error is not None:
            from robocorp_ls_core.lsp import Error

            return [Error(error, (0, 0), (1, 0)).to_lsp_diagnostic()]

        func = partial(self._threaded_lint, doc_uri)
        func = require_monitor(func)
        return func

    def _threaded_lint(self, doc_uri, monitor: IMonitor):
        from robocorp_ls_core.jsonrpc.exceptions import JsonRpcRequestCancelled
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_ROBOCOP_ENABLED,
        )
        from robocorp_ls_core import uris
        from robocorp_ls_core.lsp import Error
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_LINT_ENABLED,
        )

        try:
            from robotframework_ls.impl.ast_utils import collect_errors
            from robotframework_ls.impl import code_analysis
            import os.path

            log.debug("Lint: starting (in thread).")

            completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
            if completion_context is None:
                return []

            config = completion_context.config
            robocop_enabled = config is None or config.get_setting(
                OPTION_ROBOT_LINT_ROBOCOP_ENABLED, bool, False
            )

            ast = completion_context.get_ast()
            source = completion_context.doc.source
            monitor.check_cancelled()
            errors = collect_errors(ast)
            log.debug("Collected AST errors (in thread): %s", len(errors))
            monitor.check_cancelled()

            lint_ls_enabled = config is None or config.get_setting(
                OPTION_ROBOT_LINT_ENABLED, bool, True
            )
            if lint_ls_enabled:
                analysis_errors = code_analysis.collect_analysis_errors(
                    completion_context
                )
                monitor.check_cancelled()
                log.debug(
                    "Collected analysis errors (in thread): %s", len(analysis_errors)
                )
                errors.extend(analysis_errors)
            else:
                log.debug("Language server linting disabled.")

            lsp_diagnostics = [error.to_lsp_diagnostic() for error in errors]

            try:
                if robocop_enabled:
                    from robocorp_ls_core.robocop_wrapper import (
                        collect_robocop_diagnostics,
                    )

                    workspace = completion_context.workspace
                    if workspace is not None:
                        project_root = workspace.root_path
                    else:
                        project_root = os.path.abspath(".")

                    monitor.check_cancelled()
                    lsp_diagnostics.extend(
                        collect_robocop_diagnostics(
                            project_root, ast, uris.to_fs_path(doc_uri), source
                        )
                    )
            except Exception as e:
                log.exception(
                    "Error collecting Robocop errors (possibly an unsupported Robocop version is installed)."
                )
                lsp_diagnostics.append(
                    Error(
                        f"Error collecting Robocop errors: {e}", (0, 0), (1, 0)
                    ).to_lsp_diagnostic()
                )

            return lsp_diagnostics
        except JsonRpcRequestCancelled:
            raise JsonRpcRequestCancelled("Lint cancelled (inside lint)")
        except Exception as e:
            log.exception("Error collecting errors.")
            ret = [
                Error(
                    f"Error collecting Robocop errors: {e}", (0, 0), (1, 0)
                ).to_lsp_diagnostic()
            ]
            return ret

    def m_resolve_completion_item(
        self,
        completion_item: CompletionItemTypedDict,
        monaco=False,
    ) -> CompletionItemTypedDict:
        # Note: don't put it in a thread as it should be cheap to do in the main thread.
        use_ctx = None
        with self._completion_contexts_saved_lock:
            data = completion_item.get("data")
            if data and isinstance(data, dict):
                ctx_id = data.get("ctx")
                if ctx_id is not None:
                    for ctx in self._completion_contexts_saved:
                        if id(ctx) == ctx_id:
                            use_ctx = ctx
                            break

        if use_ctx is not None:
            use_ctx.resolve_completion_item(data, completion_item, monaco=monaco)

        return completion_item

    def m_complete_all(self, doc_uri, line, col):
        func = partial(self._threaded_complete_all, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_complete_all(self, doc_uri, line, col, monitor: IMonitor):
        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return []

        from robotframework_ls.impl import snippets_completions, section_completions

        completions = snippets_completions.complete(completion_context)
        monitor.check_cancelled()
        completions.extend(self._complete_from_completion_context(completion_context))
        completions.extend(section_completions.complete(completion_context))

        return completions

    def _complete_from_completion_context(self, completion_context):
        with self._completion_contexts_saved_lock:
            # Keep up to 3 saved contexts there (used to resolve
            # completion items afterwards).
            while len(self._completion_contexts_saved) > 2:
                self._completion_contexts_saved.popleft()
            self._completion_contexts_saved.append(completion_context)

        return complete_all(completion_context)

    def m_section_name_complete(self, doc_uri, line, col):
        from robotframework_ls.impl import section_name_completions

        completion_context = self._create_completion_context(doc_uri, line, col, None)
        if completion_context is None:
            return []

        return section_name_completions.complete(completion_context)

    def m_keyword_complete(self, doc_uri, line, col):
        from robotframework_ls.impl import keyword_completions

        completion_context = self._create_completion_context(doc_uri, line, col, None)
        if completion_context is None:
            return []
        return keyword_completions.complete(completion_context)

    def m_rename(self, doc_uri: str, line: int, col: int, new_name: str):
        func = partial(self._threaded_rename, doc_uri, line, col, new_name)
        func = require_monitor(func)
        return func

    def _threaded_rename(
        self, doc_uri: str, line: int, col: int, new_name: str, monitor: IMonitor
    ) -> WorkspaceEditTypedDict:
        from robotframework_ls.impl.rename import rename

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            raise JsonRpcException(
                "Error: unable to rename (context could not be created).", 1
            )

        return rename(completion_context, new_name)

    def m_prepare_rename(self, doc_uri: str, line: int, col: int):
        func = partial(self._threaded_prepare_rename, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_prepare_rename(
        self, doc_uri: str, line: int, col: int, monitor: IMonitor
    ) -> WorkspaceEditTypedDict:
        from robotframework_ls.impl.rename import prepare_rename

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            raise JsonRpcException(
                "Error: unable to prepare rename (context could not be created).", 1
            )

        return prepare_rename(completion_context)

    def m_flow_explorer_model(self, uri):
        func = partial(self._threaded_flow_explorer_model, uri)
        func = require_monitor(func)
        return func

    def _threaded_flow_explorer_model(self, uri, monitor) -> ActionResultDict:
        import json
        from robocorp_ls_core import uris

        # Note: it may actually be a directory (in which case we have to
        # collect the robots inside it).
        target_path = uris.to_fs_path(uri)

        completion_contexts: List[ICompletionContext] = []
        if not os.path.exists(target_path) or not os.path.isdir(target_path):
            completion_context = self._create_completion_context(uri, 0, 0, monitor)
            if completion_context is None:
                # It's a single file and we don't have a context.
                return {
                    "success": False,
                    "message": f"File: {target_path} does not exist.",
                    "result": None,
                }
            completion_contexts.append(completion_context)

        else:
            # We're dealing with a directory.
            for f in os.listdir(target_path):
                if f.endswith(".robot"):
                    f_uri = uris.from_fs_path(os.path.join(target_path, f))
                    completion_context = self._create_completion_context(
                        f_uri, 0, 0, monitor
                    )
                    if completion_context is None:
                        continue
                    completion_contexts.append(completion_context)

            if not completion_contexts:
                return {
                    "success": False,
                    "message": f"Unable to load any .robot files from: '{target_path}'.",
                    "result": None,
                }

        from robotframework_ls.impl.flow_explorer_model_builder import (
            build_flow_explorer_model,
        )

        model = build_flow_explorer_model(completion_contexts)
        if get_log_level() >= 2:
            log.debug("Model:", json.dumps(model))
        return {"success": True, "message": None, "result": model}

    def m_find_definition(self, doc_uri, line, col):
        func = partial(self._threaded_find_definition, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_find_definition(self, doc_uri, line, col, monitor) -> Optional[list]:
        from robotframework_ls.impl.find_definition import find_definition_extended
        import os.path
        from robocorp_ls_core.lsp import Location, Range
        from robocorp_ls_core import uris
        from robocorp_ls_core.lsp import LocationLink

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None
        definition_info = find_definition_extended(completion_context)

        if definition_info is None:
            return []

        origin_selection_range: Optional[
            RangeTypedDict
        ] = definition_info.origin_selection_range

        ret = []
        definition: IDefinition
        for definition in definition_info.definitions:
            if not definition.source:
                log.info("Found definition with empty source (%s).", definition)
                continue

            if not os.path.exists(definition.source):
                log.info(
                    "Found definition: %s (but source does not exist).", definition
                )
                continue

            lineno = definition.lineno
            if lineno is None or lineno < 0:
                lineno = 0

            end_lineno = definition.end_lineno
            if end_lineno is None or end_lineno < 0:
                end_lineno = 0

            col_offset = definition.col_offset
            end_col_offset = definition.end_col_offset

            if origin_selection_range is None:
                ret.append(
                    Location(
                        uris.from_fs_path(definition.source),
                        Range((lineno, col_offset), (end_lineno, end_col_offset)),
                    ).to_dict()
                )
            else:
                target_range = Range((lineno, col_offset), (end_lineno, end_col_offset))
                target_selection_range = target_range

                scope_lineno = definition.scope_lineno
                if scope_lineno is not None:
                    scope_col_offset = definition.scope_col_offset
                    if scope_col_offset is not None:
                        scope_end_lineno = definition.scope_end_lineno
                        scope_end_col_offset = definition.scope_end_col_offset
                        target_range = Range(
                            (scope_lineno, scope_col_offset),
                            (scope_end_lineno, scope_end_col_offset),
                        )

                ret.append(
                    LocationLink(
                        origin_selection_range,
                        uris.from_fs_path(definition.source),
                        target_range=target_range,
                        target_selection_range=target_selection_range,
                    ).to_dict()
                )
        return ret

    def m_code_format(self, text_document, options):
        func = partial(self._threaded_code_format, text_document, options)
        func = require_monitor(func)
        return func

    def _threaded_code_format(self, text_document, options, monitor: IMonitor):
        from robotframework_ls.impl.formatting import create_text_edit_from_diff
        from robocorp_ls_core.lsp import TextDocumentItem
        import os.path
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_CODE_FORMATTER,
        )
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY,
        )
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY,
        )

        text_document_item = TextDocumentItem(**text_document)
        text = text_document_item.text
        if not text:
            completion_context = self._create_completion_context(
                text_document_item.uri, 0, 0, monitor
            )
            if completion_context is None:
                return []
            text = completion_context.doc.source

        if not text:
            return []

        if not self._check_and_log_rf_dependency_version():
            return []

        if options is None:
            options = {}
        tab_size = options.get("tabSize", 4)

        # Default for now is the builtin. This will probably be changed in the future.
        formatter = self._config.get_setting(
            OPTION_ROBOT_CODE_FORMATTER, str, OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY
        )
        if formatter not in (
            OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY,
            OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY,
        ):
            log.critical(
                f"Code formatter invalid: {formatter}. Please select one of: {OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY}, {OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY}."
            )
            return []

        if formatter == OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY:
            try:
                from robot.tidy import Tidy
            except ImportError:
                # It's not available in newer versions of RobotFramework.
                from robotframework_ls.impl.robot_version import get_robot_major_version

                if get_robot_major_version() >= 5:
                    formatter = OPTION_ROBOT_CODE_FORMATTER_ROBOTIDY

        if formatter == OPTION_ROBOT_CODE_FORMATTER_BUILTIN_TIDY:
            from robotframework_ls.impl.formatting import robot_source_format

            new_contents = robot_source_format(text, space_count=tab_size)

        else:
            error = self._compute_min_version_error((4, 0))
            if error is not None:
                log.critical(
                    f"To use the robotidy formatter, at least Robot Framework 4 is needed. {error}"
                )
                return []

            from robocorp_ls_core.robotidy_wrapper import robot_tidy_source_format

            # Code-formatting will change the AST (even if no changes are done),
            # so, we need to create a new one for this function.
            ast = completion_context.doc.generate_ast_uncached()
            path = completion_context.doc.path
            dirname = "."
            try:
                os.stat(path)
            except:
                # It doesn't exist
                ws = self._workspace
                if ws is not None:
                    dirname = ws.root_path
            else:
                dirname = os.path.dirname(path)

            try:
                new_contents = robot_tidy_source_format(ast, dirname)
            except (ImportError, AttributeError):
                log.exception(
                    "Unable to code-format because robotidy could not be imported."
                )
                return []

        if new_contents is None or new_contents == text:
            return []
        return [x.to_dict() for x in create_text_edit_from_diff(text, new_contents)]

    def _create_completion_context(
        self, doc_uri, line, col, monitor: Optional[IMonitor]
    ):
        """
        :param line: 0-based
        :param col: 0-based
        """
        from robotframework_ls.impl.completion_context import CompletionContext

        if not self._check_and_log_rf_dependency_version():
            return None
        workspace = self.workspace
        if not workspace:
            log.info("Workspace still not initialized.")
            return None

        document = workspace.get_document(doc_uri, accept_from_file=True)
        if document is None:
            log.info("Unable to get document for uri: %s.", doc_uri)
            return None
        return CompletionContext(
            document,
            line,
            col,
            workspace=workspace,
            config=self.config,
            monitor=monitor,
            variables_from_arguments_files_loader=self._variables_from_arguments_files_loader,
            lsp_messages=self._lsp_messages,
        )

    def m_signature_help(self, doc_uri: str, line: int, col: int):
        func = partial(self._threaded_signature_help, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_signature_help(
        self, doc_uri: str, line: int, col: int, monitor: IMonitor
    ) -> Optional[dict]:
        from robotframework_ls.impl.signature_help import signature_help

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        return signature_help(completion_context)

    def m_folding_range(self, doc_uri: str):
        func = partial(self._threaded_folding_range, doc_uri)
        func = require_monitor(func)
        return func

    def _threaded_folding_range(
        self, doc_uri: str, monitor: IMonitor
    ) -> List[FoldingRangeTypedDict]:
        from robotframework_ls.impl.folding_range import folding_range

        completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
        if completion_context is None:
            return []

        return folding_range(completion_context)

    def m_selection_range(self, doc_uri: str, positions: List[PositionTypedDict]):
        func = partial(self._threaded_selection_range, doc_uri, positions)
        func = require_monitor(func)
        return func

    def _threaded_selection_range(
        self, doc_uri: str, positions: List[PositionTypedDict], monitor: IMonitor
    ) -> List[SelectionRangeTypedDict]:
        from robotframework_ls.impl.selection_range import selection_range

        completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
        if completion_context is None:
            return []

        return selection_range(completion_context, positions)

    def m_code_lens(self, doc_uri: str):
        func = partial(self._threaded_code_lens, doc_uri)
        func = require_monitor(func)
        return func

    def _threaded_code_lens(
        self, doc_uri: str, monitor: IMonitor
    ) -> List[CodeLensTypedDict]:
        from robotframework_ls.impl.code_lens import code_lens

        completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
        if completion_context is None:
            return []

        return code_lens(completion_context)

    def m_resolve_code_lens(self, **code_lens: CodeLensTypedDict):
        func = partial(self._threaded_resolve_code_lens, code_lens)
        func = require_monitor(func)
        return func

    def _threaded_resolve_code_lens(
        self, code_lens: CodeLensTypedDict, monitor: IMonitor
    ) -> CodeLensTypedDict:
        from robotframework_ls.impl.code_lens import code_lens_resolve

        data = code_lens.get("data")
        if not isinstance(data, dict):
            return code_lens

        doc_uri = data.get("uri")
        completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
        if completion_context is None:
            return code_lens

        return code_lens_resolve(completion_context, code_lens)

    def m_document_symbol(self, doc_uri: str):
        func = partial(self._threaded_document_symbol, doc_uri)
        func = require_monitor(func)
        return func

    def _threaded_document_symbol(
        self, doc_uri: str, monitor: IMonitor
    ) -> List[DocumentSymbolTypedDict]:
        from robotframework_ls.impl.document_symbol import document_symbol

        completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
        if completion_context is None:
            return []

        return document_symbol(completion_context)

    def m_list_tests(self, doc_uri: str):
        func = partial(self._threaded_list_tests, doc_uri)
        func = require_monitor(func)
        return func

    def _threaded_list_tests(
        self, doc_uri: str, monitor: IMonitor
    ) -> List[ITestInfoTypedDict]:
        from robotframework_ls.impl.code_lens import list_tests
        from pathlib import Path

        path = Path(uris.to_fs_path(doc_uri))
        if path.is_dir():
            tests = []
            for p in path.rglob("*.robot"):
                doc_uri = uris.from_fs_path(str(p))
                completion_context = self._create_completion_context(
                    doc_uri, 0, 0, monitor
                )

                if completion_context is None:
                    continue

                tests.extend(list_tests(completion_context))
            return tests
        else:
            completion_context = self._create_completion_context(doc_uri, 0, 0, monitor)
            if completion_context is None:
                return []

            return list_tests(completion_context)

    def m_collect_robot_documentation(
        self,
        doc_uri: str,
        library_name: Optional[str] = None,
        line: Optional[int] = None,
        col: Optional[int] = None,
    ):
        func = partial(
            self._threaded_collect_robot_documentation,
            doc_uri,
            library_name,
            line,
            col,
        )
        func = require_monitor(func)
        return func

    def _threaded_collect_robot_documentation(
        self,
        doc_uri: str,
        library_name: Optional[str],
        line: Optional[int],
        col: Optional[int],
        monitor: IMonitor,
    ):
        from robotframework_ls.impl.collect_robot_documentation import (
            collect_robot_documentation,
        )

        if line is None:
            line = 0
        if col is None:
            col = 0

        ctx: Optional[ICompletionContext] = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if ctx is None:
            return {
                "success": False,
                "message": "Unable to create context to generate lib docs.",
                "result": None,
            }

        try:
            return collect_robot_documentation(library_name, ctx)
        except Exception as e:
            msg = f"Error collecting documentation: {str(e)}"
            log.exception(msg)
            return {
                "success": False,
                "message": msg,
                "result": None,
            }

    def m_evaluatable_expression(self, doc_uri: str, position: PositionTypedDict):
        func = partial(self._threaded_evaluatable_expression, doc_uri, position)
        func = require_monitor(func)
        return func

    def m_rf_info(self, doc_uri: str):
        from robotframework_ls.impl.robot_version import get_robot_version

        return {"version": get_robot_version(), "python": sys.executable}

    def _threaded_evaluatable_expression(
        self, doc_uri: str, position: PositionTypedDict, monitor: IMonitor
    ) -> Optional[EvaluatableExpressionTypedDict]:
        from robotframework_ls.impl.provide_evaluatable_expression import (
            provide_evaluatable_expression,
        )

        line = position["line"]
        col = position["character"]
        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        return provide_evaluatable_expression(completion_context)

    def m_wait_for_full_test_collection(self):
        func = partial(self._threaded_wait_for_full_test_collection)
        func = require_monitor(func)
        return func

    def _threaded_wait_for_full_test_collection(self, monitor: IMonitor) -> bool:
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        workspace = self.workspace
        if not workspace:
            log.info("Workspace still not initialized.")
            return False
        ws = typing.cast(RobotWorkspace, workspace)
        workspace_indexer = ws.workspace_indexer
        if not workspace_indexer:
            raise RuntimeError("WorkspaceIndexer not available (None).")
        workspace_indexer.wait_for_full_test_collection()
        return True

    def m_hover(self, doc_uri: str, line: int, col: int):
        func = partial(self._threaded_hover, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_hover(
        self, doc_uri: str, line, col, monitor: IMonitor
    ) -> Optional[HoverTypedDict]:
        from robotframework_ls.impl.hover import hover

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        return hover(completion_context)

    def m_document_highlight(self, doc_uri: str, line: int, col: int):
        func = partial(self._threaded_document_highlight, doc_uri, line, col)
        func = require_monitor(func)
        return func

    def _threaded_document_highlight(
        self, doc_uri: str, line, col, monitor: IMonitor
    ) -> Optional[List[DocumentHighlightTypedDict]]:

        from robotframework_ls.impl.doc_highlight import doc_highlight

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        return doc_highlight(completion_context)

    def m_code_action(self, doc_uri: str, params: TextDocumentCodeActionTypedDict):
        func = partial(self._threaded_code_action, doc_uri, params)
        func = require_monitor(func)
        return func

    def _threaded_code_action(
        self, doc_uri: str, params: TextDocumentCodeActionTypedDict, monitor: IMonitor
    ) -> Optional[List[CommandTypedDict]]:

        from robotframework_ls.impl.code_action import code_action

        end = params["range"]["end"]
        line = end["line"]
        col = end["character"]
        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        context = params["context"]
        found_data: List[ICustomDiagnosticDataTypedDict] = []
        for diagnostic in context["diagnostics"]:
            data: Optional[ICustomDiagnosticDataTypedDict] = diagnostic.get("data")
            if data is not None:
                found_data.append(data)
        return code_action(completion_context, found_data)

    def m_references(
        self, doc_uri: str, line: int, col: int, include_declaration: bool
    ):
        func = partial(
            self._threaded_references, doc_uri, line, col, include_declaration
        )
        func = require_monitor(func)
        return func

    def _threaded_references(
        self, doc_uri: str, line, col, include_declaration: bool, monitor: IMonitor
    ) -> Optional[List[LocationTypedDict]]:
        from robotframework_ls.impl.references import references

        completion_context = self._create_completion_context(
            doc_uri, line, col, monitor
        )
        if completion_context is None:
            return None

        return references(completion_context, include_declaration=include_declaration)

    def m_workspace_symbols(self, query: Optional[str] = None):
        func = partial(self._threaded_workspace_symbols, query)
        func = require_monitor(func)
        return func

    def _threaded_workspace_symbols(
        self, query: Optional[str], monitor: IMonitor
    ) -> Optional[List[SymbolInformationTypedDict]]:
        from robotframework_ls.impl.workspace_symbols import workspace_symbols
        from robotframework_ls.impl.completion_context import BaseContext
        from robotframework_ls.impl.protocols import IRobotWorkspace
        from typing import cast

        workspace = self._workspace
        if not workspace:
            return []

        robot_workspace = cast(IRobotWorkspace, workspace)

        return workspace_symbols(
            query,
            BaseContext(workspace=robot_workspace, config=self.config, monitor=monitor),
        )

    def m_text_document__semantic_tokens__range(self, textDocument=None, range=None):
        raise RuntimeError("Not currently implemented!")

    def m_text_document__semantic_tokens__full(self, textDocument=None):
        func = partial(self.threaded_semantic_tokens_full, textDocument=textDocument)
        func = require_monitor(func)
        return func

    def threaded_semantic_tokens_full(
        self, textDocument: TextDocumentTypedDict, monitor: Optional[IMonitor] = None
    ):
        from robotframework_ls.impl.semantic_tokens import semantic_tokens_full

        doc_uri = textDocument["uri"]
        context = self._create_completion_context(doc_uri, -1, -1, monitor)
        if context is None:
            return {"resultId": None, "data": []}
        return {"resultId": None, "data": semantic_tokens_full(context)}

    def m_monaco_completions_from_code_full(
        self,
        prefix: str = "",
        full_code: str = "",
        position=PositionTypedDict,
        uri: str = "",
        indent: str = "",
    ):
        func = partial(
            self.threaded_monaco_completions_from_code_full,
            prefix=prefix,
            full_code=full_code,
            position=position,
            uri=uri,
            indent=indent,
        )
        func = require_monitor(func)
        return func

    def m_monaco_resolve_completion(
        self,
        completion_item: CompletionItemTypedDict,
    ):
        return self.m_resolve_completion_item(completion_item, monaco=True)

    def threaded_monaco_completions_from_code_full(
        self,
        prefix: str,
        full_code: str,
        position: PositionTypedDict,
        uri: str,
        indent: str,
        monitor: Optional[IMonitor] = None,
    ):
        from robotframework_ls.impl.robot_workspace import RobotDocument
        from robotframework_ls.impl.completion_context import CompletionContext
        from robocorp_ls_core.workspace import Document
        from robotframework_ls.impl import section_completions
        from robotframework_ls.impl import snippets_completions
        from robotframework_ls.server_api.monaco_conversions import (
            convert_to_monaco_completion,
        )
        from robotframework_ls.impl.completion_context import CompletionType

        d = Document(uri, prefix)
        last_line, _last_col = d.get_last_line_col()
        line = last_line + position["line"]

        col = position["character"]
        col += len(indent)

        document = RobotDocument(uri, full_code)
        completion_context = CompletionContext(
            document,
            line,
            col,
            config=self.config,
            monitor=monitor,
            workspace=self.workspace,
        )
        completion_context.type = CompletionType.shell
        completions = self._complete_from_completion_context(completion_context)
        completions.extend(section_completions.complete(completion_context))
        completions.extend(snippets_completions.complete(completion_context))

        return {
            "suggestions": [
                convert_to_monaco_completion(
                    c, line_delta=last_line, col_delta=len(indent), uri=uri
                )
                for c in completions
            ]
        }

    def m_semantic_tokens_from_code_full(
        self, prefix: str = "", full_code: str = "", indent: str = "", uri: str = ""
    ):
        func = partial(
            self.threaded_semantic_tokens_from_code_full,
            prefix=prefix,
            full_code=full_code,
            indent=indent,
            uri=uri,
        )
        func = require_monitor(func)
        return func

    def threaded_semantic_tokens_from_code_full(
        self,
        prefix: str,
        full_code: str,
        indent: str,
        uri: str,
        monitor: Optional[IMonitor] = None,
    ):
        from robotframework_ls.impl.semantic_tokens import semantic_tokens_full
        from robotframework_ls.impl.completion_context import CompletionContext

        try:
            from robotframework_ls.impl.robot_workspace import RobotDocument

            document = RobotDocument(uri, full_code)
            completion_context = CompletionContext(
                document,
                config=self.config,
                monitor=monitor,
                workspace=self.workspace,
            )

            data = semantic_tokens_full(completion_context)
            if not prefix:
                return {"resultId": None, "data": data}

            # We have to exclude the prefix from the coloring...

            # debug info...
            # import io
            # from robotframework_ls.impl.semantic_tokens import decode_semantic_tokens
            # stream = io.StringIO()
            # decode_semantic_tokens(data, doc, stream)
            # found = stream.getvalue()

            prefix_doc = RobotDocument("")
            prefix_doc.source = prefix
            last_line, last_col = prefix_doc.get_last_line_col()

            # Now we have the data from the full code, but we need to remove whatever
            # we have in the prefix from the result...
            ints_iter = iter(data)
            line = 0
            col = 0
            new_data = []
            indent_len = len(indent)
            while True:
                try:
                    line_delta = next(ints_iter)
                except StopIteration:
                    break
                col_delta = next(ints_iter)
                token_len = next(ints_iter)
                token_type = next(ints_iter)
                token_modifier = next(ints_iter)
                line += line_delta
                if line_delta == 0:
                    col += col_delta
                else:
                    col = col_delta

                if line >= last_line:
                    new_data.append(line - last_line)
                    new_data.append(col_delta - indent_len)
                    new_data.append(token_len)
                    new_data.append(token_type)
                    new_data.append(token_modifier)

                    # Ok, now, we have to add the indent_len to all the
                    # next lines
                    while True:
                        try:
                            line_delta = next(ints_iter)
                        except StopIteration:
                            break
                        col_delta = next(ints_iter)
                        token_len = next(ints_iter)
                        token_type = next(ints_iter)
                        token_modifier = next(ints_iter)

                        new_data.append(line_delta)
                        if line_delta > 0:
                            new_data.append(col_delta - indent_len)
                        else:
                            new_data.append(col_delta)
                        new_data.append(token_len)
                        new_data.append(token_type)
                        new_data.append(token_modifier)

                    break

                # Approach changed so that we always have a new line
                # i.e.:
                # \n<indent><code>
                #
                # so, the condition below no longer applies.
                # elif line == last_line and col >= last_col:
                #     new_data.append(0)
                #     new_data.append(col - last_col)
                #     new_data.append(token_len)
                #     new_data.append(token_type)
                #     new_data.append(token_modifier)
                #     new_data.extend(ints_iter)
                #     break

            # debug info...
            # temp_stream = io.StringIO()
            # temp_doc = RobotDocument("")
            # temp_doc.source = full_code[len(prefix) :]
            # decode_semantic_tokens(new_data, temp_doc, temp_stream)
            # temp_found = temp_stream.getvalue()

            return {"resultId": None, "data": new_data}
        except:
            log.exception("Error computing semantic tokens from code.")
            return {"resultId": None, "data": []}

    def m_shutdown(self, **_kwargs):
        PythonLanguageServer.m_shutdown(self, **_kwargs)
        self.libspec_manager.dispose()
        workspace = self._workspace
        if workspace is not None:
            workspace.dispose()

    def m_exit(self, **_kwargs):
        PythonLanguageServer.m_exit(self, **_kwargs)
        self.libspec_manager.dispose()
        workspace = self._workspace
        if workspace is not None:
            workspace.dispose()

    def m_cancel_progress(self, progressId):
        from robocorp_ls_core import progress_report

        if progress_report.cancel(progressId):
            log.info("Cancel progress %s", progressId)
            return True

        return False
