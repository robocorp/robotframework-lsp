from robocorp_ls_core.protocols import IDocument
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import IVariablesCollector
from robotframework_ls.impl.variable_types import VariableFoundFromPythonAst


log = get_logger(__name__)


def _gen_var_from_python_ast(
    variable_import_doc, collector, value_node, target_node, prefix
):
    try:
        import ast as ast_module

        varname = None
        if isinstance(target_node, (ast_module.Constant, ast_module.Str)):
            varname = target_node.s

        elif isinstance(target_node, ast_module.Name):
            varname = target_node.id

        elif isinstance(target_node, ast_module.ClassDef):
            varname = target_node.name

        if varname is not None:
            varname = str(varname)
            if varname.startswith("DICT__"):
                varname = varname[6:]
            elif varname.startswith("LIST__"):
                varname = varname[6:]

            if prefix:
                fullname = prefix + varname
            else:
                fullname = varname

            if collector.accepts(fullname):
                value = ""
                try:
                    # Only available for Python 3.8 onwards...
                    end_lineno = getattr(value_node, "end_lineno", None)
                    if end_lineno is None:
                        end_lineno = value_node.lineno

                    # Only available for Python 3.8 onwards...
                    end_col_offset = getattr(value_node, "end_col_offset", None)
                    if end_col_offset is None:
                        end_col_offset = 99999999
                    value = variable_import_doc.get_range(
                        value_node.lineno - 1,
                        value_node.col_offset,
                        end_lineno - 1,
                        end_col_offset,
                    )
                except:
                    log.exception("Error dealing with value node: %s", value_node)

                variable_found = VariableFoundFromPythonAst(
                    variable_import_doc.path,
                    target_node.lineno - 1,
                    target_node.col_offset,
                    target_node.lineno - 1,
                    target_node.col_offset + len(varname),
                    value,
                    variable_name=fullname,
                )
                collector.on_variable(variable_found)
    except:
        log.exception(
            "Error dealing with target node: %s, value node: %s",
            target_node,
            value_node,
        )


def collect_variables_from_python_ast(
    python_ast, python_doc: IDocument, collector: IVariablesCollector, prefix=""
):
    import ast as ast_module

    try:
        for node in python_ast.body:
            if isinstance(node, ast_module.AnnAssign):
                _gen_var_from_python_ast(
                    python_doc, collector, node.value, node.target, prefix=prefix
                )

            elif isinstance(node, ast_module.Assign):
                for target in node.targets:
                    _gen_var_from_python_ast(
                        python_doc, collector, node.value, target, prefix=prefix
                    )

            elif isinstance(node, ast_module.ClassDef):
                _gen_var_from_python_ast(python_doc, collector, node, node, prefix="")
                collect_variables_from_python_ast(
                    node, python_doc, collector, prefix=node.name + "."
                )

            elif isinstance(node, ast_module.FunctionDef):
                if node.name in ("get_variables", "getVariables"):
                    # https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#getting-variables-from-a-special-function
                    for b in node.body:
                        if isinstance(b, ast_module.Return):
                            if isinstance(b.value, ast_module.Dict):
                                for key, value in zip(b.value.keys, b.value.values):
                                    _gen_var_from_python_ast(
                                        python_doc, collector, value, key, prefix=prefix
                                    )
    except:
        log.exception("Error collecting variables from Python AST.")
