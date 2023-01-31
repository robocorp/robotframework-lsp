from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    ILibraryDoc,
    IKeywordFound,
    CompletionType,
)
from robocorp_ls_core.lsp import (
    CompletionItemKind,
    TextEditTypedDict,
    CompletionItemTypedDict,
    InsertTextFormat,
)
from typing import Optional, List, Set, Dict, Any
from robotframework_ls.impl.protocols import NodeInfo
import os.path
from robocorp_ls_core import uris
from robocorp_ls_core.protocols import IWorkspace
from robotframework_ls.impl.protocols import ISymbolsCache
from robotframework_ls.impl.robot_constants import ALL_KEYWORD_RELATED_FILE_EXTENSIONS


class _Collector(object):
    def __init__(
        self,
        selection,
        token,
        import_location_info: "_ImportLocationInfo",
        imported_keyword_name_to_keyword: Dict[str, List[IKeywordFound]],
        exact_match: bool,
        add_import: bool,
        prefix_module: bool,
    ):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        token_str = token.value

        self.completion_items: List[CompletionItemTypedDict] = []
        self.selection = selection
        self.import_location_info = import_location_info
        self.token = token
        self.imported_keyword_name_to_keyword = imported_keyword_name_to_keyword
        self.exact_match = exact_match
        self.add_import = add_import
        self.prefix_module = prefix_module

        self._matcher = RobotStringMatcher(token_str)

    def accepts(self, keyword_name: str) -> bool:
        if self.exact_match:
            if not self._matcher.is_same_robot_name(keyword_name):
                return False
        else:
            if not self._matcher.accepts_keyword_name(keyword_name):
                return False

        keywords_found: Optional[
            List[IKeywordFound]
        ] = self.imported_keyword_name_to_keyword.get(keyword_name)
        if not keywords_found:
            return True

        return False

    def _create_completion_item(
        self,
        completion_context: ICompletionContext,
        keyword_name: str,
        selection,
        token,
        col_delta: int,
        memo: Set[str],
        lib_import: Optional[str] = None,
        resource_path: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> Optional[CompletionItemTypedDict]:
        """
        Note: the lib_import and resource_path are the strings to be added
        so that the given library/resource is loaded.

        i.e.: It's the name concatenated to the `Library    {lib_import}` or
        `Resource    {resource_path}`.
        """
        label = f"{keyword_name} ({lib_import or resource_path})"
        if label in memo:
            return None
        memo.add(label)

        prefix = ""
        detail = ""
        if self.add_import:
            import_line = -1
            if completion_context.type != CompletionType.shell:
                if lib_import is not None:
                    import_line = self.import_location_info.get_library_import_line()
                elif resource_path is not None:
                    import_line = self.import_location_info.get_resource_import_line()

            if import_line == -1:
                # There's no existing import, so, let's see if we have a *** Settings *** section.
                # If we don't we have to create the whole settings, otherwise, we'll add the statement
                # as the first thing in the existing *** Settings *** section.
                if completion_context.type == CompletionType.shell:
                    import_line = 0
                    prefix = "*** Settings ***\n"
                elif self.import_location_info.setting_section_node_info is None:
                    import_line = 0
                    prefix = "*** Settings ***\n"
                else:
                    import_line = (
                        self.import_location_info.setting_section_node_info.node.end_lineno
                        - 1
                    )

        text = keyword_name

        if keyword_name in self.imported_keyword_name_to_keyword or self.prefix_module:
            check = lib_import or resource_path
            if check:
                basename = os.path.basename(check)
                if basename.endswith(ALL_KEYWORD_RELATED_FILE_EXTENSIONS):
                    basename = os.path.splitext(basename)[0]
                text = f"{basename}.{keyword_name}"

        text_edit: TextEditTypedDict = {
            "range": {
                "start": {
                    "line": selection.line,
                    "character": token.col_offset + col_delta,
                },
                "end": {"line": selection.line, "character": token.end_col_offset},
            },
            "newText": text,
        }

        additional_text_edits: Optional[List[TextEditTypedDict]] = None

        if not self.add_import:
            if lib_import is not None:
                detail = "* Requires Library Import"
            elif resource_path is not None:
                detail = "* Requires Resource Import"
        else:
            additional_text_edits = []
            if lib_import is not None:
                additional_text_edits.append(
                    {
                        "range": {
                            "start": {"line": import_line, "character": 0},
                            "end": {"line": import_line, "character": 0},
                        },
                        "newText": f"{prefix}Library    {lib_import}\n",
                    }
                )
                detail = "* Adds Library Import"
            elif resource_path is not None:
                additional_text_edits.append(
                    {
                        "range": {
                            "start": {"line": import_line, "character": 0},
                            "end": {"line": import_line, "character": 0},
                        },
                        "newText": f"{prefix}Resource    {resource_path}\n",
                    }
                )
                detail = "* Adds Resource Import"

        completion_item: CompletionItemTypedDict = {
            "label": f"{label}*",
            "detail": detail,
            "kind": CompletionItemKind.Reference,
            "textEdit": text_edit,
            "insertText": text_edit["newText"],
            "insertTextFormat": InsertTextFormat.Snippet,
            "additionalTextEdits": additional_text_edits,
            "data": data,
        }
        self.completion_items.append(completion_item)
        return completion_item


def _collect_auto_import_completions(
    completion_context: ICompletionContext,
    collector: _Collector,
    collect_deprecated: bool = False,
):
    from robotframework_ls.impl.workspace_symbols import iter_symbols_caches
    from robotframework_ls.robot_config import create_convert_keyword_format_func
    from robotframework_ls import robot_config
    from robotframework_ls.impl.text_utilities import has_deprecated_text

    symbols_cache: ISymbolsCache
    selection = completion_context.sel
    token = collector.token

    ws: IWorkspace = completion_context.workspace
    folder_paths = []
    for folder in ws.iter_folders():
        folder_paths.append(uris.to_fs_path(folder.uri))

    curr_doc_path = os.path.dirname(uris.to_fs_path(completion_context.doc.uri))

    memo: Set[str] = set()

    default_convert_keyword_format = create_convert_keyword_format_func(
        completion_context.config
    )
    noop = lambda x: x

    deprecated_name_to_replacement = (
        robot_config.get_robot_libraries_deprecated_name_to_replacement(
            completion_context.config
        )
    )

    for symbols_cache in iter_symbols_caches(
        None, completion_context, show_builtins=False
    ):
        library_info: Optional[ILibraryDoc] = symbols_cache.get_library_info()
        doc: Optional[IRobotDocument] = symbols_cache.get_doc()

        lib_import = None
        resource_path = None

        if library_info is not None:
            if not collect_deprecated and (
                library_info.name in deprecated_name_to_replacement
                or has_deprecated_text(library_info.doc)
            ):
                continue

            if library_info.source:
                if (
                    library_info.source
                    in collector.import_location_info.imported_libraries
                ):
                    continue
            elif library_info.name in collector.import_location_info.imported_libraries:
                continue

            if library_info.source:
                for folder_path in folder_paths:
                    # If the library is found to be in the workspace, use a relative
                    # path, otherwise use the library name (in which case it's expected
                    # to be in the pythonpath).
                    if library_info.source.startswith(folder_path):
                        try:
                            lib_import = os.path.relpath(
                                library_info.source, curr_doc_path
                            ).replace("\\", "/")
                            break
                        except:
                            pass
                else:
                    lib_import = library_info.name

            else:
                lib_import = library_info.name

            convert_keyword_format = default_convert_keyword_format

        elif doc is not None:
            resource_path = doc.path
            try:
                resource_path = os.path.relpath(resource_path, curr_doc_path).replace(
                    "\\", "/"
                )
            except:
                pass
            convert_keyword_format = noop

        for keyword_info in symbols_cache.iter_keyword_info():
            if collector.accepts(keyword_info.name):
                item = collector._create_completion_item(
                    completion_context,
                    convert_keyword_format(keyword_info.name),
                    selection,
                    token,
                    0,
                    memo,
                    lib_import=lib_import,
                    resource_path=resource_path,
                    data=None,
                )
                if item is not None:
                    completion_context.assign_documentation_resolve(
                        item, keyword_info.get_documentation
                    )


class _ImportLocationInfo:
    def __init__(self):
        self.library_node_info: Optional[NodeInfo] = None
        self.resource_node_info: Optional[NodeInfo] = None
        self.setting_section_node_info: Optional[NodeInfo] = None
        self.imported_libraries: Set[str] = set()
        self.imported_resources: Set[str] = set()

    def get_library_import_line(self) -> int:
        if self.library_node_info is not None:
            return self.library_node_info.node.end_lineno
        return -1

    def get_resource_import_line(self) -> int:
        if self.resource_node_info is not None:
            return self.resource_node_info.node.end_lineno
        return -1


def _obtain_import_location_info(completion_context) -> _ImportLocationInfo:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.libspec_manager import LibspecManager
    from robot.api import Token

    import_location_info = _ImportLocationInfo()

    # Ok, we have something, let's discover where we want to add the
    # 'Library' or 'Resource'.
    ast = completion_context.get_ast()

    libspec_manager: LibspecManager = completion_context.workspace.libspec_manager

    for node_info in ast_utils.iter_nodes(
        ast,
        accept_class=ast_utils.LIBRARY_IMPORT_CLASSES
        + ast_utils.RESOURCE_IMPORT_CLASSES
        + ast_utils.SETTING_SECTION_CLASSES,
    ):
        if ast_utils.is_library_node_info(node_info):
            import_location_info.library_node_info = node_info

            library_name_token = node_info.node.get_token(Token.NAME)
            if library_name_token is not None:
                library_doc_or_error = libspec_manager.get_library_doc_or_error(
                    completion_context.token_value_resolving_variables(
                        library_name_token
                    ),
                    create=True,
                    completion_context=completion_context,
                    args=ast_utils.get_library_arguments_serialized(node_info.node),
                )
                library_doc = library_doc_or_error.library_doc
                if library_doc is not None:
                    if library_doc.source:
                        import_location_info.imported_libraries.add(library_doc.source)
                    else:
                        import_location_info.imported_libraries.add(library_doc.name)

        elif ast_utils.is_resource_node_info(node_info) and node_info.node.name:
            import_location_info.resource_node_info = node_info
            import_location_info.imported_resources.add(node_info.node.name)

        elif ast_utils.is_setting_section_node_info(node_info):
            import_location_info.setting_section_node_info = node_info

    return import_location_info


def complete(
    completion_context: ICompletionContext,
    imported_keyword_name_to_keyword: Dict[str, List[IKeywordFound]],
    use_for_quick_fix=False,
    exact_match=False,
) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ENABLE,
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ADD_IMPORT,
        OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME,
    )

    config = completion_context.config

    if use_for_quick_fix:
        exact_match = True
    else:
        if config is not None:
            if not config.get_setting(
                OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ENABLE, bool, True
            ):
                return []

    add_import = True
    prefix_module = False
    if config is not None:
        add_import = config.get_setting(
            OPTION_ROBOT_COMPLETIONS_KEYWORDS_NOT_IMPORTED_ADD_IMPORT, bool, True
        )

        prefix_module = config.get_setting(
            OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME, bool, False
        )

    if use_for_quick_fix:
        add_import = True

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = ast_utils.get_keyword_name_token(
            token_info.stack, token_info.node, token_info.token
        )
        if token is not None:
            import_location_info = _obtain_import_location_info(completion_context)

            collector = _Collector(
                completion_context.sel,
                token,
                import_location_info,
                imported_keyword_name_to_keyword,
                exact_match=exact_match,
                add_import=add_import,
                prefix_module=prefix_module,
            )
            _collect_auto_import_completions(
                completion_context, collector, collect_deprecated=False
            )

            return collector.completion_items
    return []
