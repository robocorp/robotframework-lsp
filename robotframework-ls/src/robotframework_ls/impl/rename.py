from typing import List, Dict, Optional

from robocorp_ls_core.lsp import (
    LocationTypedDict,
    WorkspaceEditTypedDict,
    TextEditTypedDict,
    MessageType,
    RangeTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext, IKeywordDefinition
from robocorp_ls_core.jsonrpc.exceptions import JsonRpcException
import typing
from robotframework_ls.impl.robot_constants import ROBOT_AND_TXT_FILE_EXTENSIONS
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def rename(
    completion_context: ICompletionContext, new_name: str
) -> WorkspaceEditTypedDict:
    from robotframework_ls.impl.references import references

    refs: List[LocationTypedDict] = references(
        completion_context, include_declaration=True
    )
    changes: Dict[str, List[TextEditTypedDict]] = {}
    for ref in refs:
        text_range = ref["range"]
        text_edit: TextEditTypedDict = {
            "range": text_range,
            "newText": new_name,
        }

        uri = ref["uri"]

        if uri != completion_context.doc.uri and not uri.lower().endswith(
            ROBOT_AND_TXT_FILE_EXTENSIONS
        ):
            log.info("Skipping rename at: %s", uri)
            continue

        lst = changes.get(uri)
        if lst is None:
            lst = changes[uri] = []

        lst.append(text_edit)

    ret: WorkspaceEditTypedDict = {
        "changes": changes,
    }
    return ret

    # Do we have a usage to require documentChanges instead?
    #
    # changes: Dict[str, List[AnnotatedTextEditTypedDict]] = {}
    # for i, ref in enumerate(refs):
    #     text_range = ref["range"]
    #     text_edit: AnnotatedTextEditTypedDict = {
    #         "range": text_range,
    #         "newText": new_name,
    #         "annotationId": str((i % 2) + 1),
    #     }
    #
    #     uri = ref["uri"]
    #
    #     lst = changes.get(uri)
    #     if lst is None:
    #         lst = changes[uri] = []
    #
    #     lst.append(text_edit)
    #
    # document_changes: List[TextDocumentEditTypedDict] = []
    # for uri, change in changes.items():
    #     text_document_edit: TextDocumentEditTypedDict = {
    #         "textDocument": {"uri": uri, "version": None},
    #         "edits": change,
    #     }
    #     document_changes.append(text_document_edit)
    #
    # ret: WorkspaceEditTypedDict = {
    #     # "changes": changes,
    #     "documentChanges": document_changes,
    #     "changeAnnotations": {"1": "Change 1", "2": "Change 2 not supported?"},
    # }


def prepare_rename(completion_context: ICompletionContext) -> Optional[RangeTypedDict]:
    from robotframework_ls.impl.find_definition import find_definition_extended
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.protocols import IVariableDefinition

    lsp_messages = completion_context.lsp_messages

    definition_info = find_definition_extended(completion_context)
    if definition_info:
        for definition in definition_info.definitions:
            if hasattr(definition, "keyword_found"):
                keyword_definition = typing.cast(IKeywordDefinition, definition)
                keyword_found = keyword_definition.keyword_found
                library_name = keyword_found.library_name
                keyword_name = keyword_found.keyword_name

                if library_name:
                    if lsp_messages:
                        lsp_messages.show_message(
                            f"Keyword defined in Library. Only references will be renamed "
                            f"(the '{keyword_name}' definition in '{library_name}' "
                            f"will need to be renamed manually).",
                            MessageType.Warning,
                        )
                else:
                    try:
                        toks = tuple(
                            ast_utils.create_token(keyword_name).tokenize_variables()
                        )
                    except:
                        pass
                    else:
                        for tok in toks:
                            if tok.type == tok.VARIABLE:
                                raise JsonRpcException(
                                    f"Unable to rename '{keyword_name}' (keywords with variables embedded in the name cannot be renamed).",
                                    10,
                                )

                return definition_info.origin_selection_range

            if hasattr(definition, "variable_found"):
                from robotframework_ls.impl.variable_resolve import has_variable

                variable_definition = typing.cast(IVariableDefinition, definition)

                variable_name = variable_definition.variable_found.variable_name
                if has_variable(variable_name):
                    raise JsonRpcException(
                        f"Unable to rename variable definition: '{variable_name}' (variables with variables embedded cannot be renamed).",
                        10,
                    )
                return definition_info.origin_selection_range

    raise JsonRpcException(
        "Unable to rename (could not find keyword nor variable in current position).",
        10,
    )
