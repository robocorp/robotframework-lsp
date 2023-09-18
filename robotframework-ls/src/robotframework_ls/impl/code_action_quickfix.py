from typing import List, Dict, Any, Iterator, Iterable
import typing

from robocorp_ls_core.lsp import (
    CommandTypedDict,
    ICustomDiagnosticDataTypedDict,
    ICustomDiagnosticDataUndefinedKeywordTypedDict,
    WorkspaceEditTypedDict,
    CompletionItemTypedDict,
    TextEditTypedDict,
    WorkspaceEditParamsTypedDict,
    ICustomDiagnosticDataUndefinedResourceTypedDict,
    ICustomDiagnosticDataUndefinedLibraryTypedDict,
    ICustomDiagnosticDataUndefinedVarImportTypedDict,
    ICustomDiagnosticDataUnexpectedArgumentTypedDict,
    ICustomDiagnosticDataUndefinedVariableTypedDict,
    CodeActionTypedDict,
)
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IKeywordFound,
    IResourceImportNode,
    IRobotDocument,
    TokenInfo,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import isinstance_name
import os
from pathlib import Path
from robotframework_ls.impl.robot_generated_lsp_constants import (
    OPTION_ROBOT_QUICK_FIX_KEYWORD_TEMPLATE,
)
from robotframework_ls.impl._code_action_utils import (
    add_show_document_at_command,
    wrap_edit_in_command,
)

log = get_logger(__name__)


def _add_import_code_action(
    completion_context: ICompletionContext,
) -> Iterator[CodeActionTypedDict]:
    from robotframework_ls.impl.collect_keywords import (
        collect_keyword_name_to_keyword_found,
    )
    from robotframework_ls.impl import auto_import_completions

    keyword_name_to_keyword_found: Dict[
        str, List[IKeywordFound]
    ] = collect_keyword_name_to_keyword_found(completion_context)
    auto_imports_found: List[
        CompletionItemTypedDict
    ] = auto_import_completions.complete(
        completion_context,
        keyword_name_to_keyword_found,
        use_for_quick_fix=True,
    )

    for auto_import in auto_imports_found:
        label = auto_import["label"]
        if label.endswith("*"):
            label = label[:-1]

        lst: List[TextEditTypedDict] = []

        text_edit = auto_import["textEdit"]
        if text_edit:
            lst.append(text_edit)

        additional = auto_import["additionalTextEdits"]
        if additional:
            lst.extend(additional)

        changes = {completion_context.doc.uri: lst}
        edit: WorkspaceEditTypedDict = {"changes": changes}
        title = f"Import {label}"
        edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
        command: CommandTypedDict = {
            "title": title,
            "command": "robot.applyCodeAction",
            "arguments": [{"apply_edit": edit_params}],
        }

        yield {"title": title, "kind": "quickfix", "command": command}


def _create_keyword_in_current_file_text_edit(
    completion_context: ICompletionContext,
    keyword_template: str,
) -> TextEditTypedDict:
    from robotframework_ls.impl import ast_utils

    current_section: Any = completion_context.get_ast_current_section()
    if ast_utils.is_keyword_section(current_section):
        # Add it before the current keyword
        use_line = None
        for node in current_section.body:
            if isinstance_name(node, "Keyword"):
                node_lineno = node.lineno - 1

                if node_lineno <= completion_context.sel.line:
                    use_line = node_lineno
                else:
                    break

        if use_line is not None:
            return {
                "range": {
                    "start": {"line": use_line, "character": 0},
                    "end": {"line": use_line, "character": 0},
                },
                "newText": keyword_template,
            }

    keyword_section = ast_utils.find_keyword_section(completion_context.get_ast())
    if keyword_section is None:
        # We need to create the keyword section too
        current_section = completion_context.get_ast_current_section()
        if current_section is None:
            use_line = 0
        else:
            use_line = current_section.lineno - 1

        return {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": f"*** Keywords ***\n{keyword_template}",
        }

    else:
        # We add the keyword after the end of the existing keyword section
        use_line = keyword_section.end_lineno
        if completion_context.doc.get_line(use_line - 1).strip():
            keyword_template = "\n\n" + keyword_template

        elif completion_context.doc.get_line(use_line - 2).strip():
            keyword_template = "\n" + keyword_template

        return {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": keyword_template,
        }


def _undefined_variable_code_action(
    completion_context: ICompletionContext,
    undefined_variable_data: ICustomDiagnosticDataUndefinedVariableTypedDict,
) -> Iterable[CodeActionTypedDict]:
    from robotframework_ls.impl import ast_utils

    current_section: Any = completion_context.get_ast_current_section()
    if ast_utils.is_keyword_section(current_section) or ast_utils.is_testcase_section(
        current_section
    ):
        # Add it before the current keyword
        token_info = completion_context.get_current_token()
        if token_info:
            use_line = token_info.node.lineno - 1

            if use_line > 0:
                from robotframework_ls.robot_config import get_arguments_separator
                from robotframework_ls.robot_config import (
                    create_convert_keyword_format_func,
                )
                import re

                format_name = create_convert_keyword_format_func(
                    completion_context.config
                )
                set_var_name = format_name("Set Variable")
                indent = "    "
                line_contents = completion_context.doc.get_line(use_line)
                found = re.match("[\s]+", line_contents)
                if found:
                    indent = found.group()

                sep = get_arguments_separator(completion_context)
                name = undefined_variable_data["name"]
                change: TextEditTypedDict = {
                    "range": {
                        "start": {"line": use_line, "character": 0},
                        "end": {"line": use_line, "character": 0},
                    },
                    "newText": "%s${%s}=%s%s%s$__LSP_CURSOR_LOCATION__$\n"
                    % (indent, name, sep, set_var_name, sep),
                }
                yield wrap_edit_in_command(
                    completion_context,
                    "Create local variable",
                    change,
                )

                # We can also create a variable in the variables section.
                yield _undefined_variable_code_action_create_in_variables_section(
                    completion_context, undefined_variable_data
                )

                if ast_utils.is_keyword_section(current_section):
                    # We can also create an argument.
                    yield from _undefined_variable_code_action_create_argument(
                        completion_context, undefined_variable_data, token_info, sep
                    )


def _undefined_variable_code_action_create_argument(
    completion_context: ICompletionContext,
    undefined_variable_data: ICustomDiagnosticDataUndefinedVariableTypedDict,
    token_info: TokenInfo,
    sep: str,
) -> Iterable[CodeActionTypedDict]:
    from robotframework_ls.impl import ast_utils

    text_edit: TextEditTypedDict

    for node in reversed(token_info.stack):
        if isinstance_name(node, "Keyword"):
            break
    else:
        return

    for arguments_node_info in ast_utils.iter_nodes(node, "Arguments"):
        break
    else:
        arguments_node_info = None

    if arguments_node_info is not None:
        for token in reversed(arguments_node_info.node.tokens):
            if token.type in (token.ARGUMENT, token.ARGUMENTS):
                # We need to add the spacing
                use_line = token.lineno - 1
                col = token.end_col_offset
                text_edit = {
                    "range": {
                        "start": {"line": use_line, "character": col},
                        "end": {"line": use_line, "character": col},
                    },
                    "newText": "%s${%s}$__LSP_CURSOR_LOCATION__$"
                    % (sep, undefined_variable_data["name"]),
                }

                yield wrap_edit_in_command(
                    completion_context,
                    "Add to arguments",
                    text_edit,
                )
                return

        return

    # There's no [Arguments] section. Create it.
    use_line = node.lineno
    col = 0
    text_edit = {
        "range": {
            "start": {"line": use_line, "character": col},
            "end": {"line": use_line, "character": col},
        },
        "newText": "%s[Arguments]%s${%s}$__LSP_CURSOR_LOCATION__$\n"
        % (sep, sep, undefined_variable_data["name"]),
    }

    yield wrap_edit_in_command(
        completion_context,
        "Add to arguments",
        text_edit,
    )


def _undefined_variable_code_action_create_in_variables_section(
    completion_context: ICompletionContext,
    undefined_variable_data: ICustomDiagnosticDataUndefinedVariableTypedDict,
) -> CodeActionTypedDict:
    from robotframework_ls.impl.code_action_common import (
        create_var_in_variables_section_text_edit,
    )

    var_template = "${%s}    $__LSP_CURSOR_LOCATION__$\n" % (
        undefined_variable_data["name"],
    )
    text_edit = create_var_in_variables_section_text_edit(
        completion_context, var_template
    )

    return wrap_edit_in_command(
        completion_context,
        "Create variable in variables section",
        text_edit,
    )


def _create_keyword_in_current_file_code_action(
    completion_context: ICompletionContext, keyword_template: str, keyword_name: str
) -> Iterator[CodeActionTypedDict]:
    text_edit = _create_keyword_in_current_file_text_edit(
        completion_context, keyword_template
    )
    lst: List[TextEditTypedDict] = [text_edit]

    changes = {completion_context.doc.uri: lst}
    edit: WorkspaceEditTypedDict = {"changes": changes}
    title = f"Create Keyword: {keyword_name} (in current file)"
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}
    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_edit": edit_params}],
    }

    add_show_document_at_command(command, completion_context.doc.uri, text_edit)
    yield {"title": title, "kind": "quickfix", "command": command}


def _undefined_resource_code_action(
    completion_context: ICompletionContext,
    undefined_resource_data: ICustomDiagnosticDataUndefinedResourceTypedDict,
) -> Iterator[CodeActionTypedDict]:
    from robocorp_ls_core.lsp import CreateFileTypedDict
    from robocorp_ls_core import uris

    name = undefined_resource_data["resolved_name"]
    if not name:
        name = undefined_resource_data["name"]
        if not name:
            return

    if "$" in name or "{" in name or "}" in name:
        return

    path = Path(os.path.join(os.path.dirname(completion_context.doc.path), name))
    doc_uri = uris.from_fs_path(str(path))
    create_doc_change: CreateFileTypedDict = {
        "kind": "create",
        "uri": doc_uri,
    }
    edit: WorkspaceEditTypedDict = {"documentChanges": [create_doc_change]}
    title: str = f"Create {path.name} (at {path.parent})"
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}

    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_edit": edit_params}],
    }

    add_show_document_at_command(command, doc_uri)

    yield {"title": title, "kind": "quickfix", "command": command}


def _undefined_keyword_code_action(
    completion_context: ICompletionContext,
    undefined_keyword_data: ICustomDiagnosticDataUndefinedKeywordTypedDict,
) -> Iterator[CodeActionTypedDict]:
    from robotframework_ls.robot_config import get_arguments_separator

    keyword_template = "$keyword_name$keyword_arguments\n    $cursor\n\n"
    config = completion_context.config
    if config is not None:
        keyword_template = config.get_setting(
            OPTION_ROBOT_QUICK_FIX_KEYWORD_TEMPLATE, str, keyword_template
        )

    # Make it less likely that we'll have conflicts for our variables.
    keyword_template = keyword_template.replace("$cursor", "$__LSP_CURSOR_LOCATION__$")
    keyword_template = keyword_template.replace(
        "$keyword_name", "$__LSP_KEYWORD_NAME_LOCATION__$"
    )
    keyword_template = keyword_template.replace(
        "$keyword_arguments", "$__LSP_KEYWORD_ARGUMENTS_LOCATION__$"
    )

    # --- Update the arguments in the template.

    arguments: List[str] = []
    keyword_usage_info = completion_context.get_current_keyword_usage_info()
    if keyword_usage_info is not None:
        for token in keyword_usage_info.node.tokens:
            if token.type == token.ARGUMENT:
                i = token.value.find("=")
                if i > 0:
                    name = token.value[:i]
                else:
                    name = token.value
                if not name:
                    name = "arg"
                arguments.append(f"${{{name}}}")

    separator = get_arguments_separator(completion_context)
    args_str = ""
    if arguments:
        args_str += "\n    [Arguments]"
        for arg in arguments:
            args_str += separator
            args_str += arg

    keyword_template = keyword_template.replace(
        "$__LSP_KEYWORD_ARGUMENTS_LOCATION__$", args_str
    )

    # --- Update the keyword name in the template.

    # We'd like to have a cursor here, but alas, this isn't possible...
    # See: https://github.com/microsoft/language-server-protocol/issues/592
    # See: https://github.com/microsoft/language-server-protocol/issues/724
    keyword_name = undefined_keyword_data["name"]

    dots_found = keyword_name.count(".")
    if dots_found >= 2:
        # Must check for use cases... Do nothing for now.
        return

    if dots_found == 1:
        # Something as:
        # my_resource.Keyword or
        # my_python_module.Keyword
        #
        # in this case we need to create a keyword "Keyword" in "my_resource".
        # If my_module is imported, create it in that module, otherwise,
        # if it exists but we haven't imported it, we need to import it.
        # If it doesn't exist we need to create it first.
        splitted = keyword_name.split(".")
        resource_or_import_or_alias_name, keyword_name = splitted
        keyword_template = keyword_template.replace(
            "$__LSP_KEYWORD_NAME_LOCATION__$", keyword_name
        )
        yield from _deal_with_resource_or_import_or_alias_name(
            completion_context,
            resource_or_import_or_alias_name,
            keyword_template,
            keyword_name,
        )
        return

    keyword_template = keyword_template.replace(
        "$__LSP_KEYWORD_NAME_LOCATION__$", keyword_name
    )

    yield from _add_import_code_action(completion_context)
    yield from _create_keyword_in_current_file_code_action(
        completion_context, keyword_template, keyword_name
    )


def _matches_resource_import(
    resource_import: IResourceImportNode,
    name: str,
):
    from robotframework_ls.impl.text_utilities import normalize_robot_name

    name = normalize_robot_name(name)

    for token in resource_import.tokens:
        if token.type == token.NAME:
            import_name = normalize_robot_name(token.value)

            if import_name == name:
                return True

            # ./my_resource.robot -> my_resource.robot
            import_name = os.path.basename(import_name)
            if import_name == name:
                return True

            # Handle something as my_resource.robot
            import_name = os.path.splitext(import_name)[0]
            if import_name == name:
                return True

    return False


def _create_keyword_in_another_file_code_action(
    completion_context: ICompletionContext, keyword_template: str, keyword_name: str
) -> Iterator[CodeActionTypedDict]:
    text_edit = _create_keyword_in_current_file_text_edit(
        completion_context, keyword_template
    )
    lst: List[TextEditTypedDict] = [text_edit]

    changes = {completion_context.doc.uri: lst}
    edit: WorkspaceEditTypedDict = {"changes": changes}
    modname: str = os.path.basename(completion_context.doc.uri)
    title = f"Create Keyword: {keyword_name} (in {modname})"
    edit_params: WorkspaceEditParamsTypedDict = {"edit": edit, "label": title}

    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [
            {
                "apply_edit": edit_params,
            }
        ],
    }

    add_show_document_at_command(command, completion_context.doc.uri, text_edit)

    yield {"title": title, "kind": "quickfix", "command": command}


def _deal_with_resource_or_import_or_alias_name(
    completion_context: ICompletionContext,
    resource_or_import_or_alias_name: str,
    keyword_template: str,
    keyword_name: str,
) -> Iterator[CodeActionTypedDict]:
    for resource_import in completion_context.get_resource_imports():
        if _matches_resource_import(resource_import, resource_or_import_or_alias_name):
            doc = completion_context.get_resource_import_as_doc(resource_import)
            if doc is not None:
                new_completion_context = completion_context.create_copy(doc)
                yield from _create_keyword_in_another_file_code_action(
                    new_completion_context, keyword_template, keyword_name
                )


def _create_arguments_command(
    completion_context: ICompletionContext,
    use_line: int,
    use_col: int,
    arg_name: str,
    keyword_name: str,
    prefix: str = "",
    postfix: str = "",
) -> CodeActionTypedDict:
    from robotframework_ls.robot_config import get_arguments_separator

    separator = get_arguments_separator(completion_context)
    text_edit: TextEditTypedDict = {
        "range": {
            "start": {
                "line": use_line,
                "character": use_col,
            },
            "end": {
                "line": use_line,
                "character": use_col,
            },
        },
        "newText": f"{prefix}{separator}{arg_name}$__LSP_CURSOR_LOCATION__${postfix}",
    }

    changes = {completion_context.doc.uri: [text_edit]}
    edit: WorkspaceEditTypedDict = {"changes": changes}
    title = f"Add argument {arg_name} to {keyword_name}"
    edit_params: WorkspaceEditParamsTypedDict = {
        "edit": edit,
        "label": title,
    }
    command: CommandTypedDict = {
        "title": title,
        "command": "robot.applyCodeAction",
        "arguments": [{"apply_edit": edit_params}],
    }

    add_show_document_at_command(command, completion_context.doc.uri, text_edit)
    return {"title": title, "kind": "quickfix", "command": command}


def _unexpected_argument_code_action(
    completion_context: ICompletionContext,
    unexpected_argument_data: ICustomDiagnosticDataUnexpectedArgumentTypedDict,
) -> Iterable[CodeActionTypedDict]:
    from robocorp_ls_core import uris
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.string_matcher import RobotStringMatcher

    arg_name = unexpected_argument_data["arg_name"]
    if "=" not in arg_name:
        return

    arg_name = arg_name.split("=")[0]
    if not arg_name:
        return

    arg_name = "${%s}" % (arg_name,)

    keyword_name = unexpected_argument_data["keyword_name"]
    path = unexpected_argument_data["path"]
    doc = completion_context.workspace.get_document(
        uris.from_fs_path(path), accept_from_file=True
    )
    if not doc:
        return

    robotdoc = typing.cast(IRobotDocument, doc)
    completion_context = completion_context.create_copy(robotdoc)
    ast = robotdoc.get_ast()
    robot_string_matcher = RobotStringMatcher(keyword_name)
    matched_keyword_node = None
    for keyword in ast_utils.iter_keywords(ast):
        keyword_name = keyword.node.name
        if robot_string_matcher.is_keyword_name_match(keyword_name):
            matched_keyword_node = keyword.node
            break
    else:
        return

    for stmt in matched_keyword_node.body:
        if isinstance_name(stmt, "Arguments"):
            # Ok, found existing arguments
            for token in reversed(stmt.tokens):
                if token.type in (token.ARGUMENT, token.ARGUMENTS):
                    last_arg = token
                    use_line = last_arg.lineno - 1
                    use_col = last_arg.end_col_offset

                    yield _create_arguments_command(
                        completion_context,
                        use_line,
                        use_col,
                        arg_name,
                        keyword_name,
                    )
                    return

    # If we got here theres no [Arguments] section. So, create it along
    # with the arguments.
    header = matched_keyword_node.header
    prefix = f"    [Arguments]"

    yield _create_arguments_command(
        completion_context,
        use_line=header.end_lineno,
        use_col=0,
        arg_name=arg_name,
        keyword_name=keyword_name,
        prefix=prefix,
        postfix="\n",
    )


def code_action_quickfix(
    completion_context: ICompletionContext,
    found_data: List[ICustomDiagnosticDataTypedDict],
) -> Iterable[CodeActionTypedDict]:
    """
    Note: the completion context selection should be at the range end position.
    """
    ret: List[CodeActionTypedDict] = []
    for data in found_data:
        if data["kind"] == "undefined_keyword":
            undefined_keyword_data = typing.cast(
                ICustomDiagnosticDataUndefinedKeywordTypedDict, data
            )
            ret.extend(
                _undefined_keyword_code_action(
                    completion_context, undefined_keyword_data
                )
            )

        elif data["kind"] == "unexpected_argument":
            unexpected_argument_data = typing.cast(
                ICustomDiagnosticDataUnexpectedArgumentTypedDict, data
            )
            ret.extend(
                _unexpected_argument_code_action(
                    completion_context, unexpected_argument_data
                )
            )

        elif data["kind"] == "undefined_resource":
            undefined_resource_data = typing.cast(
                ICustomDiagnosticDataUndefinedResourceTypedDict, data
            )
            ret.extend(
                _undefined_resource_code_action(
                    completion_context, undefined_resource_data
                )
            )

        elif data["kind"] == "undefined_library":
            undefined_library_data = typing.cast(
                ICustomDiagnosticDataUndefinedLibraryTypedDict, data
            )
            ret.extend(
                _undefined_resource_code_action(
                    completion_context, undefined_library_data
                )
            )

        elif data["kind"] == "undefined_var_import":
            undefined_var_import_data = typing.cast(
                ICustomDiagnosticDataUndefinedVarImportTypedDict, data
            )
            ret.extend(
                _undefined_resource_code_action(
                    completion_context, undefined_var_import_data
                )
            )

        elif data["kind"] == "undefined_variable":
            undefined_variable_data = typing.cast(
                ICustomDiagnosticDataUndefinedVariableTypedDict, data
            )
            ret.extend(
                _undefined_variable_code_action(
                    completion_context, undefined_variable_data
                )
            )

    for code_action in ret:
        command = code_action["command"]
        if command and command["command"] == "robot.applyCodeAction":
            arguments = command["arguments"]
            if arguments:
                arg = arguments[0]
                lint_uris = arg.get("lint_uris")
                if lint_uris is None:
                    lint_uris = []
                    arg["lint_uris"] = lint_uris
                lint_uris.append(completion_context.doc.uri)

    return ret
