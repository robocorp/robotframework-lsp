from robotframework_ls.impl.protocols import (
    ICompletionContext,
    NodeInfo,
    ILibraryDocConversions,
)
from typing import Optional, Any
import typing
from robocorp_ls_core.lsp import HoverTypedDict
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import ActionResultDict

log = get_logger(__name__)


def _collect_html_for_non_library_element(
    ctx: ICompletionContext,
) -> Optional[HoverTypedDict]:
    from robotframework_ls.impl import hover

    return hover.hover(ctx)


def collect_robot_documentation(
    library_name: Optional[str], ctx: ICompletionContext
) -> ActionResultDict:
    try:
        return _collect_robot_documentation(library_name, ctx)
    except Exception as e:
        msg = f"Error collecting robot documentation: {str(e)}"
        log.exception(msg)

        return {
            "success": False,
            "message": msg,
            "result": None,
        }


def _collect_robot_documentation(
    library_name: Optional[str], ctx: ICompletionContext
) -> ActionResultDict:
    from robotframework_ls.impl import ast_utils

    ws = ctx.workspace
    libspec_manager = ws.libspec_manager

    # We need to create a copy (which we'll use for dealing with HTML).
    # Note that we also want to collect the original copy, not the one
    # which was converted to markdown.
    libspec_manager = libspec_manager.create_copy()

    if library_name:
        library_doc_or_error = libspec_manager.get_library_doc_or_error(
            library_name,
            create=True,
            completion_context=ctx,
        )
    else:
        ast = ctx.get_ast()
        from robot.api import Token

        line = ctx.sel.line
        col = ctx.sel.col

        section = ast_utils.find_section(ast, line)
        if not section:
            return {
                "success": False,
                "message": f"No documentation for selection at line: {line}",
                "result": None,
            }
        token_info = ast_utils.find_token(section, line, col)
        if not token_info:
            return {
                "success": False,
                "message": f"No documentation for selection in line: {line}, col: {col}",
                "result": None,
            }

        node_info: NodeInfo[Any] = NodeInfo(token_info.stack, token_info.node)
        if not ast_utils.is_library_node_info(node_info):
            # Ok, no docs for a library, let's get the hover info and provide it.
            ret = _collect_html_for_non_library_element(ctx)
            if not ret:
                return {
                    "success": False,
                    "message": f"No custom documentation available for node: {node_info.node.__class__.__name__} at line: {line}, col: {col} ",
                    "result": None,
                }
            else:
                return {
                    "success": True,
                    "message": None,
                    "result": ret,
                }

        library_name_token = node_info.node.get_token(Token.NAME)
        if library_name_token is None:
            return {
                "success": False,
                "message": f"Unable to get library name for library import in line: {line}, col: {col}.",
                "result": None,
            }

        library_doc_or_error = libspec_manager.get_library_doc_or_error(
            ctx.token_value_resolving_variables(library_name_token),
            create=True,
            completion_context=ctx,
            args=ast_utils.get_library_arguments_serialized(node_info.node),
        )

    library_doc = library_doc_or_error.library_doc
    if not library_doc:
        return {
            "success": False,
            "message": library_doc_or_error.error,
            "result": None,
        }

    try:
        typing.cast(ILibraryDocConversions, library_doc).convert_docs_to_html()
    except Exception as e:
        msg = f"Error converting docs to html: {str(e)}"
        log.exception(msg)

        return {
            "success": False,
            "message": msg,
            "result": None,
        }

    return {
        "success": True,
        "message": None,
        "result": {"libdoc_json": library_doc.to_dictionary()},
    }
