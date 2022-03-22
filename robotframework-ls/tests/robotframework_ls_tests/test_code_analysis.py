from robotframework_ls.impl.robot_version import get_robot_major_version
import pytest


def _collect_errors(workspace, doc, data_regression, basename=None, config=None):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_analysis import collect_analysis_errors

    completion_context = CompletionContext(doc, workspace=workspace.ws, config=config)

    errors = [
        error.to_lsp_diagnostic()
        for error in collect_analysis_errors(completion_context)
    ]

    def key(diagnostic):
        return (
            diagnostic["range"]["start"]["line"],
            diagnostic["range"]["start"]["character"],
            diagnostic["message"],
        )

    errors = sorted(errors, key=key)
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


def test_casing_on_filename(workspace, libspec_manager, data_regression):
    from robocorp_ls_core.protocols import IDocument
    from pathlib import Path

    # i.e.: Importing a python library with capital letters fails #143

    workspace.set_root("case4", libspec_manager=libspec_manager)
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
    doc.source = """
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


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards.")
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


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards.")
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


@pytest.mark.skipif(get_robot_major_version() < 4, reason="Requires RF 4 onwards.")
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
