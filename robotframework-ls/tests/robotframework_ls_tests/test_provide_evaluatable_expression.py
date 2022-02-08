def test_provide_evaluatable_expression_var_basic(workspace, data_regression):
    from robotframework_ls.impl.provide_evaluatable_expression import (
        provide_evaluatable_expression,
    )
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Test Cases ***
List Variable
    Log    ${NAME}"""

    line, col = doc.get_last_line_col()
    evaluatable_expression = provide_evaluatable_expression(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - 1)
    )
    data_regression.check(evaluatable_expression)


def test_provide_evaluatable_expression_in_variables(workspace, data_regression):
    from robotframework_ls.impl.provide_evaluatable_expression import (
        provide_evaluatable_expression,
    )
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Variables ***
${some variable}    22"""

    line, _col = doc.get_last_line_col()
    evaluatable_expression = provide_evaluatable_expression(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=3)
    )
    data_regression.check(evaluatable_expression)


def test_provide_evaluatable_expression_keyword(workspace, data_regression):
    from robotframework_ls.impl.provide_evaluatable_expression import (
        provide_evaluatable_expression,
    )
    from robotframework_ls.impl.completion_context import CompletionContext

    workspace.set_root("case1")
    doc = workspace.put_doc("case1.robot")
    doc.source = """*** Test Cases ***
List Variable
    Log    ${NAME}"""

    line, col = doc.get_last_line_col()
    evaluatable_expression = provide_evaluatable_expression(
        CompletionContext(
            doc, workspace=workspace.ws, line=line, col=col - len("g    ${NAME}")
        )
    )
    data_regression.check(evaluatable_expression)
