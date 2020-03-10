def test_parse_errors(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import collect_errors

    source = """*** Settings ***
Documentation     A test suite with a single test for valid login.
...
...               This test has a workflow that is created using keywords in
...               the imported resource file.
Resource          resource.txt

"test"

*** Invalid Invalid Invalid ***
    Something

*** Test Cases ***
Valid Login
    Open Browser To Login Page
    Input Username    demo
    Input Password    mode
    Submit Credentials
    Welcome Page Should Be Open
    [Teardown]    Close Browser"""

    doc = RobotDocument("unsaved", source)
    errors = collect_errors(doc.get_ast())

    data_regression.check([e.to_dict() for e in errors], basename="errors")

    data_regression.check(
        [e.to_lsp_diagnostic() for e in errors], basename="lsp_diagnostic"
    )

    assert repr(errors)  # Just check that it works.
