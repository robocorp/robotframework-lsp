import pytest

from robot import get_version
from robocorp_ls_core.basic import check_min_version

rf_version = get_version(naked=True)


def test_parse_errors(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import collect_errors
    from robotframework_ls.impl import ast_utils

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
    ast_utils.print_ast(doc.get_ast())
    errors = collect_errors(doc.get_ast())

    data_regression.check([e.to_dict() for e in errors], basename="errors")

    data_regression.check(
        [e.to_lsp_diagnostic() for e in errors], basename="lsp_diagnostic"
    )

    assert repr(errors)  # Just check that it works.


@pytest.mark.skipif(
    not check_min_version(rf_version, (4, 0)), reason="Check not supported."
)
def test_parse_errors_if(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import collect_errors
    from robotframework_ls.impl import ast_utils

    source = """
*** Test Cases ***
If without end
    IF  ${True}
       No Operation
"""

    doc = RobotDocument("unsaved", source)
    ast_utils.print_ast(doc.get_ast())
    errors = collect_errors(doc.get_ast())

    data_regression.check([e.to_dict() for e in errors], basename="errors_if")


@pytest.mark.skipif(
    not check_min_version(rf_version, (4, 0)), reason="Check not supported."
)
def test_parse_errors_for(data_regression):
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.ast_utils import collect_errors
    from robotframework_ls.impl import ast_utils

    source = """
*** Test Cases ***
Invalid END
    FOR    ${var}    IN    one    two
        Fail    Not executed
"""

    doc = RobotDocument("unsaved", source)
    ast_utils.print_ast(doc.get_ast())
    errors = collect_errors(doc.get_ast())

    data_regression.check([e.to_dict() for e in errors], basename="errors_for")
