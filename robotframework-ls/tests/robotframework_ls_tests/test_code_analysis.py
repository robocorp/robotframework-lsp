from robotframework_ls.impl.robot_version import get_robot_major_version
import pytest
from robocorp_ls_core.protocols import IDocument
from pathlib import Path


def _collect_errors(
    workspace, doc, data_regression, basename=None, config=None, transform_errors=None
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_analysis import collect_analysis_errors

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]
    if transform_errors is not None:
        errors = transform_errors(errors)

    def key(diagnostic):
        return (
            diagnostic["range"]["start"]["line"],
            diagnostic["range"]["start"]["character"],
            diagnostic["message"],
        )

    errors = sorted(errors, key=key)
    # We're not interested in the data in this case
    for error in errors:
        error.pop("data", None)
    data_regression.check(errors, basename=basename)


def test_keywords_analyzed(workspace, libspec_manager, data_regression):

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot",
        doc.source
        + ("\n    This keyword does not exist" "\n    [Teardown]    Also not there"),
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_analyzed_templates(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case2.robot",
        """*** Settings ***
Test Template    this is not there""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_no_lib_name(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case2.robot",
        """*** Settings ***
Library
Resource

*** Keywords ***
I check ${cmd}
    Log    ${cmd}
""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_with_vars_no_error(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot",
        doc.source
        + """
    I check ls
    I execute "ls" rara "-lh"

*** Keywords ***
I check ${cmd}
    Log    ${cmd}

I execute "${cmd}" rara "${opts}"
    Log    ${cmd} ${opts}
    
""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_in_args(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    doc = workspace.put_doc(
        "case2.robot",
        doc.source
        + """
    Run Keyword If    ${var}    This does not exist    
""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_in_args_no_error_with_var(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    new_source = (
        doc.source
        + """
    ${var}=    Set Variable    22
    Run Keyword    ${var}
    Run Keyword    concat with ${var}
"""
    )
    doc = workspace.put_doc("case2.robot", new_source)

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keywords_with_prefix_no_error(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    # Ignore bdd-related prefixes (see: robotframework_ls.impl.robot_constants.BDD_PREFIXES)
    doc = workspace.put_doc(
        "case2.robot",
        doc.source
        + """
    given I check ls
    then I execute

*** Keywords ***
I check ${cmd}
    Log    ${cmd}

I execute
    Log    foo
""",
    )

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keywords_prefixed_by_library(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    String
Library    Collections
Resource    case4resource.txt

*** Test Cases ***
Test
    BuiltIn.Log    Logging
    case4resource3.Yet Another Equal Redefined
    String.Should Be Titlecase    Hello World
    ${list}=    BuiltIn.Create List    1    2
    Collections.Append To List    ${list}    3""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_prefixed_with_alias(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    Collections    WITH NAME    Col1

*** Test Cases ***
Test
    ${list}=    Set Variable    1
    Col1.Append To List    ${list}    3""",
    )

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keywords_name_matches(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test
    ${list}=    Set Variable    1
    AppendToList    ${list}    3""",
    )

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_resource_does_not_exist(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    DoesNotExist
Library    .
Library    ..
Library    ../
Resource    does_not_exist.txt
Resource    ${foo}/does_not_exist.txt
Resource    ../does_not_exist.txt
Resource    .
Resource    ..
Resource    ../
Resource    ../../does_not_exist.txt
Resource    case4resource.txt

*** Test Cases ***
Test
    case4resource3.Yet Another Equal Redefined""",
    )

    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    v = get_robot_major_version()
    if v > 4:
        v = 4
    basename = f"test_resource_does_not_exist.v{v}"

    _collect_errors(workspace, doc, data_regression, config=config, basename=basename)


def test_empty_library_exists(workspace, libspec_manager, data_regression):
    workspace.set_root("case_empty_lib", libspec_manager=libspec_manager)

    doc = workspace.get_doc("case_empty_lib.robot")
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_resource_does_not_exist_2nd_level(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)

    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Resource    my_resource.robot
""",
    )

    doc2 = workspace.put_doc(
        "my_resource.robot",
        """*** Settings ***
Resource    does_not_exist_res.robot
Library    does_not_exist_lib.py
Variables    does_not_exist_var.py
""",
    )

    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_report_wrong_library(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    DoesNotExistLib
Resource    DoesNotExistRes
Variables    DoesNotExistVar
""",
    )

    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    v = get_robot_major_version()
    if v > 4:
        v = 4
    basename = f"test_report_wrong_library.v{v}"
    _collect_errors(
        workspace,
        doc,
        data_regression,
        config=config,
        basename=basename,
    )


def test_casing_on_filename(workspace, libspec_manager, data_regression, tmpdir):
    from robocorp_ls_core.protocols import IDocument
    from pathlib import Path

    # i.e.: Importing a python library with capital letters fails #143

    workspace.set_root_writable_dir(tmpdir, "case4", libspec_manager=libspec_manager)
    doc: IDocument = workspace.put_doc("case4.robot", text="")
    p = Path(doc.path)
    (p.parent / "myPythonKeywords.py").write_text(
        """
class myPythonKeywords(object):
    ROBOT_LIBRARY_VERSION = 1.0
    def __init__(self):
        pass

    def Uppercase_Keyword (self):
        return "Uppercase does not work"
"""
    )

    doc.source = """*** Settings ***
Library    myPythonKeywords.py

*** Test Cases ***
Test
    Uppercase Keyword"""

    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    # Note: we don't give errors if we can't resolve a resource.
    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)


def test_empty_teardown(workspace, libspec_manager, data_regression):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")

    doc.source = """
*** Test Cases ***
My Test 1
  [Teardown]
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_lib_with_params(
    workspace, libspec_manager, cases, data_regression
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib.robot")

    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)


def test_code_analysis_lib_with_params_2(
    workspace, libspec_manager, cases, data_regression
):
    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib3.robot")

    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)


def test_code_analysis_lib_with_params_3(
    workspace, libspec_manager, cases, data_regression
):
    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    libspec_manager.config = config

    doc = workspace.get_doc("case_params_on_lib4.robot")

    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)


def test_code_analysis_same_lib_multiple_with_alias(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case4.robot")

    doc.source = """*** Settings ***
Library    Collections    WITH NAME    col1
Library    Collections    WITH NAME    col2

*** Test Cases ***
Test
    col1.Dictionary Should Contain Item
    col2.Dictionary Should Contain Item
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_same_lib_with_alias_with_params(
    workspace, libspec_manager, cases, data_regression
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_PYTHONPATH

    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)

    caseroot = cases.get_path("case_params_on_lib")
    config = RobotConfig()
    config.update(
        {
            "robot": {
                "pythonpath": [caseroot],
                "libraries": {"libdoc": {"needsArgs": ["*"]}},
            }
        }
    )
    assert config.get_setting(OPTION_ROBOT_PYTHONPATH, list, []) == [caseroot]
    libspec_manager.config = config

    doc = workspace.put_doc("case_params_on_lib.robot")
    doc.source = """
*** Settings ***
Library   LibWithParams    some_param=foo    WITH NAME   LibFoo
Library   LibWithParams    some_param=bar    WITH NAME   LibBar

*** Test Case ***
My Test
    LibFoo.Foo Method
    LibBar.Bar Method
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error", config=config)


def test_code_analysis_search_pythonpath(
    workspace, libspec_manager, cases, data_regression
):
    import sys

    add_to_pythonpath = cases.get_path("case_search_pythonpath_resource/resources")
    sys.path.append(add_to_pythonpath)

    try:
        workspace.set_root(
            "case_search_pythonpath_resource", libspec_manager=libspec_manager
        )

        doc = workspace.get_doc("case_search_pythonpath.robot")

        _collect_errors(workspace, doc, data_regression, basename="no_error")
    finally:
        sys.path.remove(add_to_pythonpath)


@pytest.mark.skipif(
    get_robot_major_version() < 5, reason="Only supported in RF 5 onwards."
)
def test_code_analysis_variable_search_pythonpath(
    workspace, libspec_manager, cases, data_regression
):
    import sys

    add_to_pythonpath = cases.get_path("case_search_pythonpath_variable")
    sys.path.append(add_to_pythonpath)

    try:
        workspace.set_root(
            "case_search_pythonpath_variable", libspec_manager=libspec_manager
        )

        doc = workspace.get_doc("case_search_pythonpath.robot")

        _collect_errors(workspace, doc, data_regression, basename="no_error")
    finally:
        sys.path.remove(add_to_pythonpath)


@pytest.mark.skipif(
    get_robot_major_version() < 5, reason="Only supported in RF 5 onwards."
)
def test_code_analysis_variable_search_init_pythonpath(
    workspace, libspec_manager, cases, data_regression
):
    import sys

    add_to_pythonpath = cases.get_path("case_search_pythonpath_variable")
    sys.path.append(add_to_pythonpath)

    try:
        workspace.set_root(
            "case_search_pythonpath_variable", libspec_manager=libspec_manager
        )

        doc = workspace.get_doc("case_search_pythonpath_init.robot")

        _collect_errors(workspace, doc, data_regression, basename="no_error")
    finally:
        sys.path.remove(add_to_pythonpath)


def test_code_analysis_template_name_keyword(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keyword ***
Example Keyword

*** Test Cases **
Normal test case
    Example keyword    first argument    second argument

Templated test case
    [Template]    Example k
    first argument    second argument
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_too_many_arguments(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
No arg
    Log To Console      22

*** Test Cases **
Normal test case
    No arg    22
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_arguments_pos_after_named(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword all
    [Arguments]    ${arg1}    ${arg2}    @{arg3}   &{arg4}
    Log To Console      ${arg1} ${arg2} ${arg3} &{arg4}
    
Keyword named and star
    [Arguments]     ${arg1}   @{arg3}
    Log To Console     ${arg3}

Keyword only star
    [Arguments]     @{arg3}
    Log To Console     ${arg3}

*** Test Cases **
Normal test case
    Keyword all    arg1=22   pos_after_named
    Keyword named and star    arg1=22   pos_after_named
    Keyword only star    arg1=22   this is ok
    Keyword named and star    arg1   foo=22    22
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_pos_in_keyword(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  &{arg3}

*** Test Cases **
Normal test case
    Keyword named and keyword    arg1=ok    arg3=ok    arg4=ok
    Keyword named and keyword    arg3=ok    arg1=ok    arg4=ok
    Keyword named and keyword    ok    not ok
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_missing_arg(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  &{arg3}
    Log to console    22

*** Test Cases **
Normal test case
    Keyword named and keyword    arg2=still missing arg1
    Keyword named and keyword    ok    not ok here
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_no_match(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  @{arg3}
    Log to console    22

*** Test Cases **
Normal test case
    Keyword named and keyword    arg1=ok    arg2=not ok
    Keyword named and keyword    arg1    arg2=ok here    arg3=ok here too    anything    arg4=ok
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_no_match_2(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  @{arg3}    &{arg4}
    Log to console    22

*** Test Cases **
Normal test case
    Keyword named and keyword    arg1=ok    arg4=ok
    Keyword named and keyword    ok    ok    arg4=ok
    Keyword named and keyword    arg1=ok    not ok    arg4=ok
    Keyword named and keyword    arg1=ok    arg4=ok    not ok    arg5=not ok
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_star_and_keyword(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword star and keyword
    [Arguments]     @{arg3}    &{arg4}
    Log to console    22

*** Test Cases **
Normal test case
    Keyword star and keyword    a    b    f=2    not ok
    Keyword star and keyword    f=2    not ok 2
    Keyword star and keyword    a    b    f=2
    Keyword star and keyword    a
    Keyword star and keyword
    Keyword star and keyword    f=3
    Keyword star and keyword    f=3    g=4
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_argspec_empty_ok(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Settings ***
Library    case_argspec_expand.py

*** Test Cases **
Normal test case
    arg_with_default_empty_arg    arg1
    arg_with_default_none_arg    arg1
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_argspec_misleading(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  @{arg3}

*** Test Cases **
Normal test case
    # Because we start to match arg1 as named, the others don't match.
    Keyword named and keyword    arg1=ok  arg3=not ok    arg4=not ok
    
    # Here 'arg3=ok' makes it into arg1, so, as it wasn't matched as named
    # we can match the star args even with equals in them.
    Keyword named and keyword    arg3=ok    arg4=ok
    Keyword named and keyword    arg3=ok   arg2=ok   arg4=ok
    Keyword named and keyword    arg3=ok   arg2=ok   ok    arg3=ok=foo
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_argspec_multiple_arg1(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  ${arg2}  @{arg3}
    Log to console    22 ${arg1} @{arg3}

*** Test Cases **
Normal test case
    Keyword named and keyword    arg3=ok   arg1=not ok
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_argspec_expand_keyword_args(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Keywords ***
Keyword 4
    [Arguments]     &{arg2}
    Log to console    22

*** Test Cases ***
Test
    ${dct} =     Create dictionary    a=1    b=2
    Keyword 4    &{dct}
    Keyword 4    &{dct}    a=1
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_argspec_run_keyword(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Task ***
Some task
    Run keyword    Log to console    anything    stream=STDOUT
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_argspec_run_keyword_wrong_arguments_to_target(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Task ***
Some task
    Run keyword    Log to console    stream=STDOUT
    Run keyword Unless    a<2   Log to console    stream=STDOUT
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_argspec_library(workspace, libspec_manager, data_regression):
    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_params_on_lib.robot")
    doc.source = """
*** Settings ***
Library    AnotherLibWithParams   param1=foo   foo=not ok
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_show_why_unresolved_library(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_params_on_lib.robot")
    doc.source = """
*** Settings ***
Library    LibWithParams
"""

    v = get_robot_major_version()
    if v > 4:
        v = 4
    basename = f"test_code_analysis_show_why_unresolved_library.v{v}"

    _collect_errors(workspace, doc, data_regression, basename=basename)


def test_code_analysis_multiple_errors(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")

    doc.source = """
*** Keywords ***
Keyword 0
    Log to console    22

Keyword 1
    [Arguments]     ${arg1}
    Log to console    22
    
Keyword 2
    [Arguments]     ${arg1}  ${arg2}
    Log to console    22
    
Keyword 3
    [Arguments]     ${arg1}  @{arg2}
    Log to console    22
    
Keyword 4
    [Arguments]     ${arg1}  &{arg2}
    Log to console    22

*** Test Cases **
Normal test case
    Keyword 0    not ok
    Keyword 0    not=ok
    
    Keyword 1
    Keyword 1    arg1=1    arg2=not ok
    Keyword 1    arg2=1    arg1=not ok
    Keyword 1    arg    not ok
    
    Keyword 2    arg2=1    arg3=2
    Keyword 2
    Keyword 2    1
    Keyword 2    arg2=1
    Keyword 2    arg1=1
"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_run_keyword_if_basic(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Tasks ***
Minimal task
    ${Cond1}=    Set local variable    ${Cond1}    1
    Run Keyword If    ${Cond1}    No operation    ELSE    No operation
    Run Keyword If    ${Cond1}    No operation    ELSE IF   ${Cond1}   No operation
    Run Keyword If    ${Cond1}    No operation    ELSE IF   ${Cond1}   No operation    ELSE    No operation
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_arg_mismatches(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Test Cases ***
My Test Case
    My Keyword    options=value
    My Keyword    options = value
    My Keyword    opt ions= value
    My Keyword    Options= value
    My Keyword    o ptions= value
    # Only the last one is an error because ${text} isn't matched.
    My Keyword    O ptions= value


*** Keywords ***
My Keyword
    [Arguments]    ${text}    ${O ptions}=${EMPTY}
    Log to console    ----
    Log to console    text=${text}
    Log to console    options=${options}
"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_run_keyword_if_errors_internal(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Keywords ***
Keyword 0
    Log to console    22
    
*** Tasks ***
Minimal task
    ${Cond1}=    Set local variable    ${Cond1}    1
    ${Cond}=     Set variable   1
    Run Keyword If    ${Cond1}    Keyword 0    wrong arg 0
    Run Keyword If    ${Cond1}    Keyword 0    wrong arg 1    ELSE    Keyword 0    wrong arg 2
    Run Keyword If    ${Cond1}    Keyword 0    wrong arg 3    ELSE IF    ${cond}    Keyword 0    wrong arg 4
"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_ignore_eq_after_slash(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = r"""
*** Test Cases ***
My Test Case 2
    My Keyword 2    options \= value
    #My Keyword 2    options \= value    opt=value
    #My Keyword 2    specifiedText\=withEqual    opt=value

    #My Keyword 2    text=options = value    opt=value
    #My Keyword 2    text=specifiedText\=withEqual    opt=value

    # Only this is an error
    # My Keyword 2    options = value

*** Keywords ***
My Keyword 2
    [Arguments]    ${text}    &{options}
    No Operation
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_multiple_no_errors(workspace, libspec_manager, data_regression):
    workspace.set_root("case_argspec_expand", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_argspec_expand.robot")
    doc.source = """
*** Keywords ***
Keyword 0
    Log to console    22

Keyword 1
    [Arguments]     ${arg1}
    Log to console    22
    
Keyword 2
    [Arguments]     ${arg1}  ${arg2}
    Log to console    22
    
Keyword 3
    [Arguments]     ${arg1}  @{arg2}
    Log to console    22
    
Keyword 4
    [Arguments]     ${arg1}  &{arg2}
    Log to console    22
    
Keyword 5
    [Arguments]    ${arg}=${None}
    [Return]    ${arg}
    
Keyword 6
    [Arguments]    ${arg}
    [Return]    ${arg}


*** Test Cases **
Normal test case
    Keyword 0
    
    Keyword 1    foo
    Keyword 1    arg1=1
    Keyword 1    arg2=1
    Keyword 1    arg2=1 =3
    
    Keyword 2    arg1=1    arg2=2
    Keyword 2    arg2=1    arg1=2
    Keyword 2    any    arg2=any
    Keyword 2    arg3=foo    arg4=bar
    Keyword 2    arg3=foo    arg2=bar
    
    Keyword 3    arg1=1
    Keyword 3    arg1    arg2    arg3
    Keyword 3    arg1    arg2=foo    arg3=bar
    Keyword 3    arg1    arg2=foo    arg3=bar    any
    
    Keyword 4    arg1=1
    Keyword 4    arg1    arg2=2    arg3=3
    Keyword 4    arg1=1    arg2=foo    arg3=bar
    Keyword 4    arg2=foo    arg3=bar    arg1=1

    Keyword 5
    Keyword 5    call
    Keyword 5    arg=call    
    
    ${starargs}   Set variable    22
    ${kwargs}     Set variable    22
    Keyword 6    @{starargs}    &{kwargs}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_deprecated_keyword(workspace, libspec_manager, data_regression):
    workspace.set_root("case_params_on_lib", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case_params_on_lib.robot")
    doc.source = """
*** Keyword ***
Deprecated keyword
    [Documentation]    *DEPRECATED*    Ok, this is deprecated
    Log to console    Deprecated
    
*** Task ***
Some task
    Deprecated Keyword
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_deprecated_library(
    workspace, libspec_manager, data_regression, tmpdir
):
    from robocorp_ls_core import uris

    workspace.set_root_writable_dir(tmpdir, "case2", libspec_manager=libspec_manager)

    my_lib_uri = workspace.get_doc_uri("my_lib.py")
    p = Path(uris.to_fs_path(my_lib_uri))
    p.write_text(
        """
class my_lib:
    "*DEPRECATED*"
    def lib_keyword(self):
        pass
"""
    )
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Library    ./my_lib.py

*** Test Case ***
Test    
    lib keyword"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_none(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Test Setup    none
Test Template    None
Test Timeout    NONE

*** Test Cases ***
My Test Case
    [Setup]    none
    [Template]    NONE
    [Tags]     NONE
    [Timeout]    NONE
    Should Be True    ${TRUE}

"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_report_undefined_vars_in_imports(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource    ${unresolved}/foo.robot
Library    ${unresolved}/foo.py
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_report_undefined_variables_basic(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Case ***
Some test
    Log to console    ${unresolved}
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_report_undefined_variables_in_vars(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
&{SOME DICT}    cwd=${unresolved}
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_report_undefined_variables_custom_args(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example test case
    Something specified with type: foo and reference: bar

*** Keywords ***
Something specified with type: ${type} and reference: ${reference}
    Log to console    ${type} ${reference} ${undefined}
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_ignore_report_undefined_variables(
    workspace, libspec_manager, data_regression
):

    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Case ***
Some test
    Log to console    ${unresolved} ${UN resolved}
"""

    config = RobotConfig()
    config.update({"robot.lint.ignoreVariables": ["unresolved"]})

    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_code_analysis_ignore_report_undefined_environment_variables(
    workspace, libspec_manager, data_regression
):

    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Case ***
Some test
    Log to console    %{UNRESOLVED}
"""

    config = RobotConfig()
    config.update({"robot.lint.ignoreEnvironmentVariables": ["unresolved"]})

    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_extended_variable_syntax(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Case ***
Some test
    ${number}=    Set Variable    ${-2}
    ${Object}=    Set Variable    22
    Log to console    ${Object.foo}
    Log to console    ${Object[2]}
    Log to console    ${Object * 2}
    Log to console    ${empty}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_variable_no_error_1(workspace, libspec_manager, data_regression):
    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Dictionary variable item
    Log Many    ${USER}[name]    ${USER}[password]
    Log Many    Welcome ${USER}[name]!

Key defined as variable
    Log Many    ${DICT}[${KEY}]    ${DICT}[${42}]

Attribute access
    Log Many    ${USER.name}    ${USER.password}
    Log Many    Welcome ${USER.name}!
"""

    config = RobotConfig()
    config.update({"robot.lint.ignoreVariables": ["user", "dict"]})
    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_variable_no_error_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.robot_config import RobotConfig

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    ${OBJECT} =    Set Variable    22
    ${OBJECT.name} =    Set Variable    New name
    ${OBJECT.new_attr} =    Set Variable    New attribute
"""

    config = RobotConfig()
    config.update({"robot.lint.ignoreVariables": ["user", "dict"]})
    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_variable_in_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${JOHN HOME}    /home/john
${JANE HOME}    /home/jane

*** Test Cases ***
Example
    ${name} =    Set Variable    John
    Log    ${${name} HOME}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_variable_evaluation(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    Log to console    ${{"foo"}}
    Log to console    ${{[1, 2, 3, 4]}}, ${{ {'id': 1, 'name': 'Example', 'children': [7, 9]} }}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_var_from_for(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    FOR  ${i}  IN  ${{[1, 2, 3]}}
        Log    ${i}
    END
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_var_from_args_used_in_for(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Sample Keyword
    [Arguments]    ${some_argument}
    FOR    ${i}    IN RANGE    3
        Log    ${some_argument}
    END
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_var_undefinded_in_for(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Sample Keyword
    FOR    ${i}    IN     @{lst}
        Log    ${i}
    END
"""

    _collect_errors(workspace, doc, data_regression)


@pytest.mark.skipif(
    get_robot_major_version() <= 4, reason="RETURN only available from RF 5 onwards"
)
def test_var_undefinded_in_return(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Sample Keyword
    RETURN    ${value}
"""

    _collect_errors(workspace, doc, data_regression)


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_var_from_except_as(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    TRY
        No operation
    EXCEPT    AS    ${ee}
        Log    ${ee}
    END
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_var_from_inline_if(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    ${v}=    IF    1    Evaluate    2    ELSE    Evaluate    4
    Log    ${v}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_env_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    Log    %{not_there}
    Log    %{PATH}
"""

    _collect_errors(workspace, doc, data_regression)


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards.")
def test_var_in_expression(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    IF    $rc > ${rc2}
        Log    22
    END
"""

    _collect_errors(workspace, doc, data_regression)


def test_inner_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    Log    ${a+${b}+${c}}
"""

    _collect_errors(workspace, doc, data_regression)


def test_inner_var_2(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${per}            PER

*** Test Cases ***
Example
    Should Be True    @{${PER}SONS} == ['John', 'Jane']
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_options(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Example
    Log    ${OPTIONS}[include]
"""

    if get_robot_major_version() >= 5:
        basename = "no_error"
    else:
        basename = None  # Default
    _collect_errors(workspace, doc, data_regression, basename=basename)


def test_vars_from_py(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc_py = workspace.put_doc("vars.py")
    doc_py.source = """
from typing import Dict

VALUES: Dict[str, int] = {}
VALUES["foo"] = 1
VALUES["bar"] = 2

FOO: str = "foo"
BAR: int = 1
"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Variables    vars.py

*** Test Cases ***
Demo
    Log    ${VALUES}
    Log    ${FOO}
    Log    ${BAR}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_vars_not_undefined(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = r"""
*** Variables ***
@{DEFAULT_LIST}     @{EMPTY}

*** Test Cases ***
Import Variables Should Not Cause Undefined Variables
    @{SUITE_LIST_1} =    Set Variable    ${DEFAULT_LIST}
    Set Suite Variable    \@{SUITE_LIST_1}    one    two
    Set Suite Variable    @{SUITE_LIST_2}    three   four
    Set Suite Variable    @SUITE_LIST_3    five   six
    Should Be Equal    ${SUITE_LIST_1}[0]    one
    Suite Variable Should Be Defined In Keyword

*** Keywords ***
Suite Variable Should Be Defined In Keyword
    Should Be Equal    ${SUITE_LIST_1}[0]    one
    Should Be Equal    ${SUITE_LIST_2}[0]    three
    Should Be Equal    ${SUITE_LIST_3}[0]    five
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_local_vars_not_undefined(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Get Return Data Amount Due
  Set Local Variable  ${return_data_amount_due}  xpath://h2/div[3]
  Log to console  ${return_data_amount_due}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_env_var_with_default_value(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Env var with default value
    Should Be Equal    %{SOME_VAR=defaultvalue}    defaultvalue
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_no_error_with_vars_in_template(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Sum Test
    [Template]    Sum ${a} And ${b} Should Be ${expected_sum}
    1    2    3
    3    4    7

*** Keywords ***
Sum ${a} And ${b} Should Be ${expected_sum}
    ${sum}    Evaluate    ${a} + ${b}
    Should Be Equal As Integers    ${sum}    ${expected_sum}"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_no_error_with_constructed_vars(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Some Test Case
    [Setup]    Initialize Variables
    Log    ${SOME_VARIABLE_0}
    Log    ${SOME_VARIABLE_1}
    Log    ${SOME_VARIABLE_2}

*** Keywords ***
Initialize Variables
    FOR    ${index}    IN RANGE    3
        Set Test Variable    ${SOME_VARIABLE_${index}}    Value ${index}
    END
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_vars_from_get_variables(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc_py = workspace.put_doc("vars.py")
    doc_py.source = """
def get_variables(arg):
    return {"PYTHON_VARIABLE": arg}
"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Variables    vars.py    arg1

*** Test Cases ***
Demo
    Log    ${PYTHON_VARIABLE}
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_wait_until_keyword_succeeds(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
ret
    ${ret}=    Wait Until Keyword Succeeds    5m    10s    Echo Post    foo    bar
    ${ret}=    Wait Until Keyword Succeeds    5m    10s    Undefinedkeyword    foo    bar

echo post
    [Arguments]    ${foo}    ${bar}

    Log To Console    ${foo} ${bar}
"""

    _collect_errors(workspace, doc, data_regression)


def test_variable_pass_execution_if(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
foo
    Pass Execution If    ${undefined1}    message
    Pass Execution If    $undefined2    message
"""

    _collect_errors(workspace, doc, data_regression)


def test_variable_pass_evaluate(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
foo
    Evaluate    ${undefined1}
    Evaluate    $undefined2
"""

    _collect_errors(workspace, doc, data_regression)


@pytest.mark.skipif(get_robot_major_version() < 5, reason="Requires RF 5 onwards.")
def test_variable_inline_if(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
foo
    ${a}=    Evaluate    1
    IF  $a<${undefined1}    Log    message
    IF  $a<$undefined2    Log    message
"""
    _collect_errors(workspace, doc, data_regression)


def test_variable_defined_afterwards(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
foo
    ${a}    Evaluate    1
    ${b}    Evaluate    $a+$b
    ${c}    Evaluate    $b+1
"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_set_local_variable(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Tasks ***
Minimal task
    Set local variable    $Cond1    1
    Log to Console    ${Cond1}
    Set local variable    ${Cond2}    2
    Log to Console    ${Cond2}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_default_var_based_on_previous(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = r"""
*** Test Cases ***
Demo
    Default With Variable Based On Earlier Argument

*** Keywords ***
Default With Variable Based On Earlier Argument
    [Arguments]    ${a}=a    ${b}=b    ${c}=${a}+${b}    ${d}=${c.upper()}    ${e}=\${d}on\\t escape (\\${a})
    Should Be Equal    ${a}+${b}    ${c}
    Should Be Equal    ${c.upper()}    ${d}
    Should Be Equal    ${e}    \${d}on\\t escape (\\${a})
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_default_var_based_on_previous_2(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
${VAR}            Variable value

*** Keywords ***
Default With Variable Based On Earlier Argument
    [Arguments]    ${a}=a    ${b}=b    ${c}=${a}+${b}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_default_var_not_based_on_next(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Default With Variable Not Based On Next Argument
    [Arguments]    ${a}=${b}    ${b}=${a}
    Log to Console    ${a}+${b}

"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_args_with_vars(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword 1
    [Arguments]    ${a}=a    ${b}=b
    No Operation
    
*** Test Cases ***
Test
    ${a}=    Evaluate    "a"
    Keyword1    b=2    ${a}=A
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_args_with_vars_2(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword 1
    [Arguments]    ${a}    ${b}
    No Operation
    
*** Test Cases ***
Test
    ${a}=    Evaluate    "a"
    Keyword1    b=2    ${a}=A
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_args_with_vars_3(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword 1
    [Arguments]    ${a}    ${b}
    No Operation
    
*** Test Cases ***
Test
    ${a}=    Evaluate    "a"
    Keyword1    ${a}=A    b=2
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_arg_multiple_times(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword 1
    [Arguments]    ${a}    ${b}
    No Operation
    
*** Test Cases ***
Test
    # This is valid in RF, but it's strange, so, let's complain about it.
    Keyword1    a=1    b=2    a=3
"""
    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_var_ok(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Test
    Log to console                  ${{{1}}}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_environment_var_set(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Library                  OperatingSystem

*** Test Cases ***
Test
    Set Environment Variable         PI_NUMBER    3.14
    Log to console    %{PI_NUMBER}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_vars_in_parameters_defined(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = r"""
*** Test Cases ***
Example
    I execute "ls"
    I execute "ls" with "-lh"
    I type 1 + 2
    I type 53 - 11
    Today is 2011-06-27

*** Keywords ***
I execute "${cmd:[^"]+}"
    Log to console    ${cmd}

I execute "${cmd}" with "${opts}"
    Log to console    ${cmd} ${opts}    shell=True

I type ${num1:\d+} ${operator:[+-]} ${num2:\d+}
    Log to console    ${num1}    ${operator}    ${num2}

Today is ${date:\d{4}-\d{2}-\d{2}}
    Log to console    ${date}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_literal_val(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Integer Variables With Base
    Log to console    ${0B0}
    Log to console    ${0O0}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_var_used_to_resolve_env_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Library         OperatingSystem

*** Test Cases ***
Environment Variable With Internal Variables
    Set Environment Variable  yet_another_env_var  THIS_ENV_VAR
    ${normal_var} =  Set Variable  IS_SET
    Should Be Equal  %{%{yet_another_env_var}_${normal_var}}  Env var value
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_py_expr(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Environment Variable With Internal Variables
    Should Be True    repr(${12345}) == '12345'
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_inner_outer_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Environment Variable With Internal Variables
    Log    ${whatever ${nonexisting}}
"""
    _collect_errors(workspace, doc, data_regression)


def test_embedded_arg(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Check
    Given this "someItem" anotherArg

*** Keywords ***
${prefix:Given|When|Then} this "${item}" ${no good name for this arg ...}
    Log to console    ${item}-${no good name for this arg ...}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_no_var_found_extended(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Check
    Log    @{OBJJ.name}
"""
    _collect_errors(workspace, doc, data_regression)


def test_empty_default_env_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Check
    Log    %{undefined=}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_empty_var(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Check
    Log    %{}
"""
    _collect_errors(workspace, doc, data_regression)


def test_comment_keyword_vars(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Check
    Comment    ${var} Set Variable Test
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_undefined_reference_default_arg_value(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Keywords ***
Keyword
    [Arguments]     ${bar}=${foo}
    Log     ${bar}
    """
    _collect_errors(workspace, doc, data_regression)


def test_vars_in_get_variables(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("list_and_dict_variable_file.py")
    doc.source = """
from collections import OrderedDict


def get_variables(*args):
    if args:
        return dict((args[i], args[i+1]) for i in range(0, len(args), 2))
    list_ = ['1', '2', 3]
    tuple_ = tuple(list_)
    dict_ = {'a': 1, 2: 'b', 'nested': {'key': 'value'}}
    ordered = OrderedDict((chr(o), o) for o in range(97, 107))
    open_file = open(__file__)
    closed_file = open(__file__)
    closed_file.close()
    return {'LIST__list': list_,
            'LIST__tuple': tuple_,
            'LIST__generator': (i for i in range(5)),
            'DICT__dict': dict_,
            'DICT__ordered': ordered,
            'scalar_list': list_,
            'scalar_tuple': tuple_,
            'scalar_generator': (i for i in range(5)),
            'scalar_dict': dict_,
            'failing_generator': failing_generator,
            'failing_dict': FailingDict({1: 2}),
            'open_file': open_file,
            'closed_file': closed_file}
"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Variables           ./list_and_dict_variable_file.py

*** Variables ***
@{EXP LIST}         1    2    ${3}

*** Test Cases ***
Valid list
    Should Be Equal    ${LIST}    ${EXP LIST}
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_import_library_keyword(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Test case 1
    ${lst}=    Evaluate    []
    Import library    Collections
    Append to list    ${lst}    1    2
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_import_library_keyword_with_name(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Test case 1
    ${lst}=    Evaluate    []
    Import library    Collections    WITH NAME    Col
    Col.Append to list    ${lst}    1    2
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_for_each_input_work_item(workspace, libspec_manager, data_regression):
    from pathlib import Path

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case2.robot")
    p = Path(doc.path)
    p = p.parent
    my_library_path = p / "my_library2.py"
    my_library_path.write_text(
        """
def for_each_input_work_item(
    keyword_or_func,
    *args,
    items_limit: int = 0,
    return_results: bool = True,
    **kwargs,
):
    print('OK')
""",
        "utf-8",
    )

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Setting ***
Library    my_library2.py
    
*** Test Cases ***
Test case 1
    For each input work item    No operation
    For each input work item    No operation    items_limit=0
    For each input work item    No operation    items_limit=0    return_results=False
    For each input work item    No operation    items_limit=0    return_results=False    invalid_arg=True
    For each input work item    No operation    invalid_arg1    items_limit=0    return_results=False
    
*** Keywords ***
Some Keyword
    No operation
"""
    _collect_errors(workspace, doc, data_regression)


def test_templates_in_test_case(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Normal test case
    Example keyword    first argument    second argument
    Example keyword    first argument    second argument    third is error

Templated test case
    [Template]    Example keyword
    first argument    second argument
    first argument    second argument    third is error

*** Keywords ***
Example keyword
    [Arguments]    ${arg1}    ${arg2}
    Log to console    ${arg1} - ${arg2}
    """

    _collect_errors(workspace, doc, data_regression)


def test_templates_in_setup(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Test Template    Example keyword

*** Test Cases ***
Normal test case
    first argument    second argument
    first argument    second argument    third is error

Templated test case
    [Template]    Example keyword 2
    first argument    second argument
    first argument    second argument    third is error

*** Keywords ***
Example keyword
    [Arguments]    ${arg1}    ${arg2}
    Log to console    ${arg1} - ${arg2}

Example keyword 2
    [Arguments]    ${arg1}    ${arg2}    ${arg3}
    Log to console    ${arg1} - ${arg2} - ${arg3}
    """

    _collect_errors(workspace, doc, data_regression)


def test_templates_none(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Test Template    Example keyword

*** Test Cases ***
Normal test case
    first argument    second argument
    first argument    second argument    third is error

Templated test case
    [Template]    None
    Example keyword 2    first argument    second argument
    Example keyword 2    first argument    second argument    third is needed

*** Keywords ***
Example keyword
    [Arguments]    ${arg1}    ${arg2}
    Log to console    ${arg1} - ${arg2}

Example keyword 2
    [Arguments]    ${arg1}    ${arg2}    ${arg3}
    Log to console    ${arg1} - ${arg2} - ${arg3}
    """

    _collect_errors(workspace, doc, data_regression)


def test_templates_undefined(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Test Template    undefined

*** Test Cases ***
Normal test case
    first argument    second argument
    first argument    second argument    third is error

Templated test case
    [Template]    undefined 2
    first argument    second argument
    first argument    second argument    third is error
    """

    _collect_errors(workspace, doc, data_regression)


def test_templates_kw_with_args(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Template with kw with args 1
    [Template]    Add ${a} and ${b} equals ${c}
    1    2    3
    # Note that this should be reported as an error, but we currently
    # don't support it (to do in the future).
    1    2    3    4
    
Template with kw with args 2
    [Template]    Add 1 and ${b} equals ${c}
    1    2
    # Note that this should be reported as an error, but we currently
    # don't support it (to do in the future).
    1    2    3

*** Keywords ***
Add ${a} and ${b} equals ${c}
    Log to console    ${a} ${b} ${c}
    """
    _collect_errors(workspace, doc, data_regression, basename="no_error")


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards.")
def test_var_with_math_operators(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Test Cases ***
Template with kw with args 1
    ${a-b}=    Evaluate    22
    IF    ${a-b} == ${a-b}
        Log to console    ${a-b}    
    END
    """
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_preference_to_robot_variables(
    workspace, libspec_manager, data_regression
):

    from robotframework_ls.robot_config import RobotConfig
    import os

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource        ${RESOURCES_PATH}${/}keywords.resource

Force Tags      vscode


*** Variables ***
${RESOURCES_PATH}      22   # Defined in RF Language Server extension settings


*** Test Cases ***
Dummy Test Case
    Common Keyword
"""

    config = RobotConfig()
    config.update({"robot.variables": {"RESOURCES_PATH": os.path.dirname(doc.path)}})
    libspec_manager.config = config

    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_variables_cls(workspace, libspec_manager, data_regression):
    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_file_cls.robot", accept_from_file=True)

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_variables_curdir(workspace, libspec_manager, data_regression):
    workspace.set_root("case_vars_file", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case_vars_curdir.robot", accept_from_file=True)

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_resolve_caches(workspace, libspec_manager, data_regression, tmpdir):
    import os
    import pathlib
    import threading

    workspace.set_root_writable_dir(
        tmpdir, "case_vars_file", libspec_manager=libspec_manager
    )
    doc = workspace.put_doc("case_vars_curdir.robot")

    doc.source = """
*** Settings ***
Variables           ${CURDIR}${/}not there now${/}common variables.yaml


*** Test Cases ***
Test
    Log    ${COMMON_2}    console=True
"""

    def transform_errors(errors):
        ret = []
        for dct in errors:
            message = dct["message"]
            # Change something as:
            # Note: resolved name: c:\\Users\\xxx\\pytest-5350\\res áéíóú0\\case_vars_file\\not there now\\common variables.yaml
            # to:
            # Note: resolved name: xxx
            if "resolved name" in message:
                import re

                assert "common variables.yaml" in message

                message = re.sub(
                    "Note: resolved name: (.*)", "Note: resolved name: xxx", message
                )
                dct["message"] = message

            ret.append(dct)
        return ret

    _collect_errors(
        workspace,
        doc,
        data_regression,
        transform_errors=transform_errors,
        basename="test_resolve_caches",
    )
    event = threading.Event()

    def on_file_changed(src_path):
        if src_path.lower().endswith(".yaml"):
            event.set()

    workspace.ws.on_file_changed.register(on_file_changed)

    path = os.path.dirname(doc.path)
    p = pathlib.Path(os.path.join(path, "not there now", "common variables.yaml"))
    p.parent.mkdir()

    p.write_text(
        """
COMMON_1: 10
COMMON_2: 20
""",
        encoding="utf-8",
    )
    workspace.ws.wait_for_check_done(8)
    assert event.wait(2)
    try:
        _collect_errors(workspace, doc, data_regression, basename="no_error")
    except Exception as e:
        if not event.is_set():
            raise AssertionError("Note: event not set in expected timeout.") from e
        raise


def test_duplicated_keywords_still_analyze_args(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Keywords ***
My Keyword
    No Operation
"""

    doc2 = workspace.put_doc("case2.robot")

    doc2.source = """
*** Keywords ***
My Keyword
    No Operation
"""

    doc3 = workspace.put_doc("case3.robot")

    doc3.source = """
*** Settings ***
Resource    case1.robot
Resource    case2.robot

*** Test Case ***
My Test
    My Keyword    invalid arg
"""
    _collect_errors(workspace, doc3, data_regression)


def test_duplicated_keywords(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")

    doc.source = """
*** Keywords ***
My Keyword
    No Operation
"""

    doc2 = workspace.put_doc("case2.robot")

    doc2.source = """
*** Keywords ***
My Keyword
    No Operation
"""

    doc3 = workspace.put_doc("case3.robot")

    doc3.source = """
*** Settings ***
Resource    case1.robot
Resource    case2.robot

*** Test Case ***
My Test
    My Keyword
"""
    _collect_errors(workspace, doc3, data_regression)

    doc3.source = """
*** Settings ***
Resource    case1.robot
Resource    case2.robot

*** Test Case ***
My Test
    case1.My Keyword
    case2.My Keyword
"""
    _collect_errors(workspace, doc3, data_regression, basename="no_error")


def test_duplicated_keywords_with_alias(workspace, libspec_manager, data_regression):
    workspace.set_root("case_duplicated", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Settings ***
Library    ./RecLibrary1.py
Library    ./RecLibrary2.py    WITH NAME    foobar

*** Test Case ***
My Test
    No Operation
"""
    _collect_errors(workspace, doc, data_regression)

    doc.source = """
*** Settings ***
Library    ./RecLibrary1.py
Library    ./RecLibrary2.py    WITH NAME    foobar

*** Test Case ***
My Test
    foobar.No Operation
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_no_duplicated_keywords_different_imports(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case_duplicated_from_lib", libspec_manager=libspec_manager)
    doc = workspace.get_doc("root.robot", True)
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_duplicated_overrides_builtin(workspace, libspec_manager, data_regression):
    workspace.set_root("case_duplicated", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Settings ***
Library    ./RecLibrary1.py

*** Test Case ***
My Test
    No Operation
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_duplicated_in_same_file(workspace, libspec_manager, data_regression):
    workspace.set_root("case_duplicated", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my.resource")
    doc.source = """
*** keywords ***
Some keyword
    No Operation
    
Some Keyword
    No Operation
"""

    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Settings ***
Resource    ./my.resource

*** Test Case ***
My Test
    Some Keyword
"""
    _collect_errors(workspace, doc, data_regression)


def test_duplicated_in_same_file_redefined(workspace, libspec_manager, data_regression):
    workspace.set_root("case_duplicated", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my.resource")
    doc.source = """
*** keywords ***
Some keyword
    No Operation
    
Some Keyword
    No Operation
"""

    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Settings ***
Resource    ./my.resource

*** Test Case ***
My Test
    Some Keyword
    
*** keywords ***
Some keyword
    No Operation
    
Some Keyword
    No Operation
"""
    _collect_errors(workspace, doc, data_regression)


def test_duplicated_overridden_in_file(workspace, libspec_manager, data_regression):
    workspace.set_root("case_duplicated", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Settings ***
Library    ./RecLibrary1.py
Library    ./RecLibrary2.py    WITH NAME    foobar

*** Test Case ***
My Test
    No Operation

*** Keyword ***
No Operation
    Log to console    foo
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_given_in_keyword_name(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case.robot")

    doc.source = """
*** Test Case ***
My Test
    Given something

*** Keyword ***
Given something
    Log to console    foo
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keyword_regexp(workspace, libspec_manager, data_regression):
    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case.robot")

    doc.source = r"""
*** Test Case ***
My Test
    Today is Tuesday and tomorrow is Wednesday

*** Keyword ***
Today is ${day1:\w\{6,9\}} and tomorrow is ${day2:\w{6,9}}
    No operation
"""
    _collect_errors(workspace, doc, data_regression, basename="no_error")


@pytest.mark.parametrize("found", [False, True])
def test_code_analysis_environment_variable_in_resource_import(
    workspace, libspec_manager, data_regression, found, monkeypatch
):

    if found:
        monkeypatch.setenv("ENV_VAR_IN_RESOURCE_IMPORT", "./my")
    else:
        monkeypatch.setenv("ENV_VAR_IN_RESOURCE_IMPORT", "./my_not_found")

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource        %{ENV_VAR_IN_RESOURCE_IMPORT}/keywords.resource


*** Test Cases ***
Dummy Test Case
    Common Keyword
"""

    _collect_errors(
        workspace, doc, data_regression, basename="no_error" if found else None
    )


@pytest.mark.parametrize("found", [True, False])
def test_code_analysis_environment_variable_in_resource_import_2(
    workspace, libspec_manager, data_regression, found, monkeypatch
):
    if found:
        monkeypatch.setenv("ENV_VAR_IN_RESOURCE_IMPORT", "./my")
    else:
        monkeypatch.setenv("ENV_VAR_IN_RESOURCE_IMPORT", "./my_not_found")

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/bar/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource    ${RESOURCES}/keywords.resource


*** Variables ***
${RESOURCES}    %{ENV_VAR_IN_RESOURCE_IMPORT}/bar
"""

    _collect_errors(
        workspace, doc, data_regression, basename="no_error" if found else None
    )


def test_code_analysis_arguments_correct(workspace, libspec_manager, data_regression):

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("keywords.robot")
    doc.source = """
*** Test Cases ***
DemoCase
    Run Keyword And Continue On Failure    Check Something    name=test

*** Keywords ***
Check Something
    [Arguments]    ${name}
    Fail    ${name}"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_arguments_correct_2(workspace, libspec_manager, data_regression):

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("keywords.robot")
    doc.source = """
*** Test Cases ***
Mandatory arguments
    ${result} =    Kw Only Arg    kwo=value

*** Keywords ***
Kw Only Arg
    [Arguments]    @{}    ${kwo}
    [Return]    ${kwo}"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_arguments_handling_of_starargs(
    workspace, libspec_manager, data_regression, tmpdir
):

    workspace.set_root_writable_dir(tmpdir, "case2", libspec_manager=libspec_manager)
    doc: IDocument = workspace.put_doc("case.robot", text="")
    p = Path(doc.path)

    (p.parent / "mypylib.py").write_text(
        """
def check_python_keyword(a, b="default", *varargs):
    print(a, b, varargs)
"""
    )

    doc.source = """
*** Settings ***
Library    ./mypylib.py

*** Test Cases ***
Call1
    # This is wrong because a=ooops is not valid for Python as it'll set the a=ooops as a keyword argument.
    Check Python Keyword    A    B   a=ooops
    
    # The same thing is valid for Robot Framework because a=ooops will be consumed as a single string.
    Check RF Keyword    A    B   a=ooops

*** Keywords ***
Check RF Keyword
    [Arguments]    ${A}    ${B}=1    @{C}
    No operation
    """

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_environment_variable_default_value(
    workspace, libspec_manager, data_regression, monkeypatch
):
    monkeypatch.setenv("ENV_VAR_IN_RESOURCE_IMPORT", "./my")

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/bar/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource    %{RESOURCES_ENV=${RESOURCES}}/keywords.resource


*** Variables ***
${RESOURCES}    %{ENV_VAR_IN_RESOURCE_IMPORT}/bar
"""

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_code_analysis_environment_variable_in_resource_import_3(
    workspace, libspec_manager, data_regression
):

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/bar/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource    ${RESOURCES}/keywords.resource


*** Variables ***
${RESOURCES}    %{ENV_VAR_IN_RESOURCE_IMPORT}/bar
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_environment_variable_in_resource_import_4(
    workspace, libspec_manager, data_regression
):

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/bar/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword"""

    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Settings ***
Resource    ${RESOURCES}/keywords.resource


*** Variables ***
${RESOURCES}    %{not_there1}${not_there2}/bar
"""

    _collect_errors(workspace, doc, data_regression)


def test_code_analysis_unused_keyword(workspace, libspec_manager, data_regression):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )

    config = RobotConfig()
    config.update({OPTION_ROBOT_LINT_UNUSED_KEYWORD: True})
    libspec_manager.config = config

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my/bar/keywords.resource")
    doc.source = """
*** Keywords ***
Common Keyword
    Log to console    Common keyword
    
Keyword 2
    Log to console    Common keyword
    
    """

    _collect_errors(workspace, doc, data_regression, config=config)


def test_code_analysis_no_unused_keyword(workspace, libspec_manager, data_regression):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )

    config = RobotConfig()
    config.update({OPTION_ROBOT_LINT_UNUSED_KEYWORD: True})
    libspec_manager.config = config

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("my.robot")
    doc.source = """
*** Test Cases ***
My Test
    my task 222


*** Keywords ***
My task ${something}
    Log    ${something}
    """

    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_code_analysis_unused_change(
    workspace, libspec_manager, data_regression, workspace_dir
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )

    config = RobotConfig()
    config.update({OPTION_ROBOT_LINT_UNUSED_KEYWORD: True})
    libspec_manager.config = config

    workspace.set_absolute_path_root(workspace_dir, libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.resource",
        """
*** Keywords ***
Common Keyword
    Log to console    Something
    
Unused Keyword
    Common Keyword    #Just to mark it as used.
    """,
    )

    _collect_errors(
        workspace,
        doc,
        data_regression,
        config=config,
        basename="test_code_analysis_unused_change_unused",
    )

    _doc_use_unused = workspace.put_doc(
        "use_it_now.robot",
        """
*** Settings ***
Resource    ./my.resource

*** Test Cases ***
Mark unused used
    Unused keyword
    """,
    )

    _collect_errors(
        workspace,
        doc,
        data_regression,
        config=config,
        basename="no_error",
    )


def test_code_analysis_unused_resource_import(
    workspace, libspec_manager, data_regression, workspace_dir
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )

    config = RobotConfig()
    config.update({OPTION_ROBOT_LINT_UNUSED_KEYWORD: True})
    libspec_manager.config = config

    workspace.set_absolute_path_root(workspace_dir, libspec_manager=libspec_manager)

    doc1 = workspace.put_doc(
        "res1.resource",
        """
*** Keywords ***
Use this keyword
    Log to console    Something
    """,
    )
    doc2 = workspace.put_doc(
        "res2.resource",
        """
*** Keywords ***
Use this keyword
    Log to console    Something
    """,
    )

    _doc_use_unused = workspace.put_doc(
        "use_it_now.robot",
        """
*** Settings ***
Resource    ./res1.resource
Resource    ./res2.resource

*** Test Cases ***
Mark as used used
    res1.use this keyword
    res2.use this keyword
    """,
    )

    _collect_errors(
        workspace,
        doc1,
        data_regression,
        config=config,
        basename="no_error",
    )
    _collect_errors(
        workspace,
        doc2,
        data_regression,
        config=config,
        basename="no_error",
    )


def test_code_analysis_unused_change_on_disk(
    workspace, libspec_manager, data_regression, workspace_dir
):
    from robotframework_ls.robot_config import RobotConfig
    from robotframework_ls.impl.robot_generated_lsp_constants import (
        OPTION_ROBOT_LINT_UNUSED_KEYWORD,
    )
    from robocorp_ls_core.basic import wait_for_non_error_condition
    import os

    config = RobotConfig()
    config.update({OPTION_ROBOT_LINT_UNUSED_KEYWORD: True})
    libspec_manager.config = config

    workspace.set_absolute_path_root(workspace_dir, libspec_manager=libspec_manager)

    doc = workspace.put_doc(
        "my.resource",
        """
*** Keywords ***
Common Keyword
    Log to console    Something
    
Unused Keyword
    Common Keyword    #Just to mark it as used.
    """,
    )

    _collect_errors(
        workspace,
        doc,
        data_regression,
        config=config,
        basename="test_code_analysis_unused_change_unused",
    )

    import pathlib

    os.makedirs(workspace_dir, exist_ok=True)
    use_it_now = pathlib.Path(workspace_dir) / "use_it_now.robot"
    use_it_now.write_text(
        """
*** Settings ***
Resource    ./my.resource

*** Test Cases ***
Mark unused used
    Unused keyword
    """
    )

    def check():
        try:
            _collect_errors(
                workspace,
                doc,
                data_regression,
                config=config,
                basename="no_error",
            )
        except Exception as e:
            return str(e)
        return None

    # It'll turn out ok when our indexes are updated based on changes in the
    # filesystem.
    wait_for_non_error_condition(check)
