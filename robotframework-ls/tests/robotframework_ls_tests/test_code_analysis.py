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

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
        doc.source
        + ("\n    This keyword does not exist" "\n    [Teardown]    Also not there"),
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_analyzed_templates(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case1.robot",
        """*** Settings ***
Test Template    this is not there""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_no_lib_name(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case1.robot",
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc = workspace.put_doc(
        "case1.robot",
        doc.source
        + """
    Run Keyword If    ${var}    This does not exist    
""",
    )

    _collect_errors(workspace, doc, data_regression)


def test_keywords_in_args_no_error_with_var(
    workspace, libspec_manager, data_regression
):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    new_source = (
        doc.source
        + """
    Run Keyword    ${var}
    Run Keyword    concat with ${var}
"""
    )
    doc = workspace.put_doc("case1.robot", new_source)

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_keywords_with_prefix_no_error(workspace, libspec_manager, data_regression):
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    # Ignore bdd-related prefixes (see: robotframework_ls.impl.robot_constants.BDD_PREFIXES)
    doc = workspace.put_doc(
        "case1.robot",
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
    AppendToList    ${list}    3""",
    )

    _collect_errors(workspace, doc, data_regression, basename="no_error")


def test_resource_does_not_exist(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.robot_version import get_robot_major_version

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
Resource    does_not_exist.robot
Library    does_not_exist.py
""",
    )

    from robotframework_ls.robot_config import RobotConfig

    config = RobotConfig()
    _collect_errors(workspace, doc, data_regression, config=config, basename="no_error")


def test_report_wrong_library(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.robot_version import get_robot_major_version

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """*** Settings ***
Library    DoesNotExist
Resource    DoesNotExist
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case1.robot")
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
    from robotframework_ls.impl.robot_version import get_robot_major_version

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
