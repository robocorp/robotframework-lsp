from robocorp_ls_core.basic import isinstance_name
from robocorp_ls_core.lsp import TextEditTypedDict
from robotframework_ls.impl.protocols import ICompletionContext


def create_var_in_variables_section_text_edit(
    completion_context: ICompletionContext, var_template: str
) -> TextEditTypedDict:
    from robotframework_ls.impl import ast_utils

    # Find if there's a variables section already...
    variable_section = ast_utils.find_variable_section(completion_context.get_ast())
    text_edit: TextEditTypedDict
    if variable_section is None:
        # We need to create the variables section too
        current_section = completion_context.get_ast_current_section()
        if current_section is None:
            use_line = 0
        else:
            use_line = current_section.lineno - 1

        text_edit = {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": f"*** Variables ***\n{var_template}\n",
        }

    else:
        # We add the variable after the end of the existing variables section
        last_stmt = None
        for stmt in reversed(variable_section.body):
            if not isinstance_name(stmt, "EmptyLine"):
                last_stmt = stmt
                break

        if last_stmt is not None:
            use_line = last_stmt.end_lineno
        else:
            use_line = variable_section.header.end_lineno

        text_edit = {
            "range": {
                "start": {"line": use_line, "character": 0},
                "end": {"line": use_line, "character": 0},
            },
            "newText": var_template,
        }

    return text_edit
