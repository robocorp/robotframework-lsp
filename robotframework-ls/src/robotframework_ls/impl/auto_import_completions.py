from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    ILibraryDoc,
    IKeywordFound,
)
from robocorp_ls_core.lsp import CompletionItemKind
from typing import Optional, List, Set, Dict, Any
from robotframework_ls.impl.protocols import NodeInfo
import os.path
from robocorp_ls_core import uris


class _Collector(object):
    def __init__(
        self,
        selection,
        token,
        import_location_info: "_ImportLocationInfo",
        imported_keyword_name_to_keyword: Dict[str, List[IKeywordFound]],
    ):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher

        token_str = token.value

        self.completion_items: List[dict] = []
        self.selection = selection
        self.import_location_info = import_location_info
        self.token = token
        self.imported_keyword_name_to_keyword = imported_keyword_name_to_keyword

        self._matcher = RobotStringMatcher(token_str)

    def accepts(self, symbols_entry):
        keyword_name = symbols_entry["name"]
        if not self._matcher.accepts_keyword_name(keyword_name):
            return False

        keywords_found: List[IKeywordFound] = self.imported_keyword_name_to_keyword.get(
            keyword_name
        )
        if not keywords_found:
            return True

        # No longer do this check: if there's some symbol imported already, don't
        # try to match with the filename (just don't show it).
        #
        # This change was done because the check below wasn't perfect
        # and because it can be a bit confusing since everything imported
        # works as a wild import in RobotFramework (so, even if it was a different
        # keyword from a different place, importing it would make it clash and
        # thus such a completion is kind of strange).
        #
        # for keyword_found in keywords_found:
        #     if (
        #         uris.from_fs_path(keyword_found.source)
        #         == symbols_entry["location"]["uri"]
        #     ):
        #         return False
        # return True

        return False

    def create_completion_item(
        self,
        completion_context: ICompletionContext,
        keyword_name,
        selection,
        token,
        col_delta: int,
        memo: Set[str],
        lib_import: Optional[str] = None,
        resource_path: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> None:
        """
        Note: the lib_import and resource_path are the strings to be added
        so that the given library/resource is loaded.
        
        i.e.: It's the name concatenated to the `Library    {lib_import}` or
        `Resource    {resource_path}`.
        """
        from robocorp_ls_core.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robocorp_ls_core.lsp import MarkupKind
        from robotframework_ls.impl.protocols import CompletionType

        label = f"{keyword_name} ({lib_import or resource_path})"
        if label in memo:
            return
        memo.add(label)

        prefix = ""
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

        if keyword_name in self.imported_keyword_name_to_keyword:
            check = lib_import or resource_path
            if check:
                basename = os.path.basename(check)
                if basename.endswith((".txt", ".py", ".robot", ".resource")):
                    basename = os.path.splitext(basename)[0]
                text = f"{basename}.{keyword_name}"

        text_edit = TextEdit(
            Range(
                start=Position(selection.line, token.col_offset + col_delta),
                end=Position(selection.line, token.end_col_offset),
            ),
            text,
        )

        additional_text_edits: List[TextEdit] = []

        if lib_import is not None:
            additional_text_edits.append(
                TextEdit(
                    Range(start=Position(import_line, 0), end=Position(import_line, 0)),
                    f"{prefix}Library    {lib_import}\n",
                )
            )
        elif resource_path is not None:
            additional_text_edits.append(
                TextEdit(
                    Range(start=Position(import_line, 0), end=Position(import_line, 0)),
                    f"{prefix}Resource    {resource_path}\n",
                )
            )

        # text_edit = None
        self.completion_items.append(
            CompletionItem(
                label,
                kind=CompletionItemKind.Reference,
                text_edit=text_edit,
                insertText=text_edit.newText,
                documentation="",
                insertTextFormat=InsertTextFormat.Snippet,
                documentationFormat=MarkupKind.PlainText,
                additionalTextEdits=additional_text_edits,
                data=data,
            ).to_dict()
        )


def _collect_auto_import_completions(
    completion_context: ICompletionContext, collector: _Collector
):
    from robotframework_ls.impl.workspace_symbols import iter_symbols_caches
    from robotframework_ls.impl.protocols import ISymbolsCache
    from robocorp_ls_core.protocols import IWorkspace
    from robotframework_ls.robot_config import create_convert_keyword_format_func

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

    for symbols_cache in iter_symbols_caches(
        None, completion_context, show_builtins=False
    ):
        library_info: Optional[ILibraryDoc] = symbols_cache.get_library_info()
        doc: Optional[IRobotDocument] = symbols_cache.get_doc()

        lib_import = None
        resource_path = None

        if library_info is not None:
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

        json_list = symbols_cache.get_json_list()
        for entry in json_list:
            if collector.accepts(entry):
                collector.create_completion_item(
                    completion_context,
                    convert_keyword_format(entry["name"]),
                    selection,
                    token,
                    0,
                    memo,
                    lib_import=lib_import,
                    resource_path=resource_path,
                    data=None,
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

    import_location_info = _ImportLocationInfo()

    # Ok, we have something, let's discover where we want to add the
    # 'Library' or 'Resource'.
    ast = completion_context.get_ast()

    libspec_manager = completion_context.workspace.libspec_manager

    for node_info in ast_utils.iter_nodes(
        ast,
        accept_class=ast_utils.LIBRARY_IMPORT_CLASSES
        + ast_utils.RESOURCE_IMPORT_CLASSES
        + ast_utils.SETTING_SECTION_CLASSES,
    ):
        if ast_utils.is_library_node_info(node_info):
            import_location_info.library_node_info = node_info

            library_name = node_info.node.name
            if library_name:
                library_doc = libspec_manager.get_library_info(
                    completion_context.token_value_resolving_variables(library_name),
                    create=True,
                    current_doc_uri=completion_context.doc.uri,
                )
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
):
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None:
        token = ast_utils.get_keyword_name_token(token_info.node, token_info.token)
        if token is not None:
            import_location_info = _obtain_import_location_info(completion_context)

            collector = _Collector(
                completion_context.sel,
                token,
                import_location_info,
                imported_keyword_name_to_keyword,
            )
            _collect_auto_import_completions(completion_context, collector)

            return collector.completion_items
    return []
