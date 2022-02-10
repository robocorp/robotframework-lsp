def test_signature_help_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help
    from robocorp_ls_core.lsp import MarkupKind

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Test Cases ***
Log It
    Log    """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    result = signature_help(completion_context)
    signatures = result["signatures"]

    # Don't check the signature documentation in the data regression so that the
    # test doesn't become brittle.
    docs = signatures[0].pop("documentation")
    assert sorted(docs.keys()) == ["kind", "value"]
    assert docs["kind"] == MarkupKind.Markdown
    assert "Log" in docs["value"]
    data_regression.check(result)


def test_signature_help_parameters_in_1st_eol(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_in_1st(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_in_1st_single_space(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1 """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_in_2nd_two_spaces(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1  """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_in_2nd_eol(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1    """,
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_in_2nd(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1    arg2""",
    )

    lineno, col = doc.get_last_line_col()
    for i in range(6):
        check_col = col - i
        completion_context = CompletionContext(
            doc, line=lineno, col=check_col, workspace=workspace.ws
        )
        try:
            data_regression.check(signature_help(completion_context))
        except:
            raise AssertionError(f"Failed on i: {i}")


def test_signature_help_parameters_na(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1    arg2""",
    )

    # Checking `Some keywor|d |   arg1    arg2`
    lineno, _col = doc.get_last_line_col()
    for check_col in [16, 17]:
        completion_context = CompletionContext(
            doc, line=lineno, col=check_col, workspace=workspace.ws
        )
        try:
            data_regression.check(signature_help(completion_context))
        except:
            raise AssertionError(f"Failed on col: {check_col}")


def test_signature_help_parameters_first(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg1    arg2""",
    )

    # Checking `Some keyword |   a|rg1    arg2`
    lineno, _col = doc.get_last_line_col()
    for check_col in [18, 19, 20, 21, 22]:
        completion_context = CompletionContext(
            doc, line=lineno, col=check_col, workspace=workspace.ws
        )
        try:
            data_regression.check(signature_help(completion_context))
        except:
            raise AssertionError(f"Failed on col: {check_col}")


def test_signature_help_parameters_switch(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}
    Log To Console      ${arg1} ${arg2}
        
*** Test Cases ***
Log It
    Some keyword    arg2=m""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_star_arg_keyword(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}    @{arg3}
    Log To Console      ${arg1} ${arg2} ${arg3}

*** Test Cases ***
Test case 1
    Some Keyword    val    another    foo    bar""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_keyword_arg_keyword(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}    @{arg3}    &{arg4}
    Log To Console      ${arg1} ${arg2} ${arg3}

*** Test Cases ***
Test case 1
    Some Keyword    val    another    foo    bar    some=1    another=2""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_name_after_stararg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}    @{arg3}    &{arg4}
    Log To Console      ${arg1} ${arg2} ${arg3}

*** Test Cases ***
Test case 1
    Some Keyword    val    another    foo    bar    some=1    anot""",
    )

    # Note: must match last because it's after a keyword arg.

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_only_stararg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Keyword only star
    [Arguments]     @{arg3}
    Log To Console     ${arg3}

*** Test Cases **
Normal test case
    Keyword only star    arg1=22   this is ok""",
    )

    lineno, col = doc.get_last_line_col()
    col -= len("1=22   this is ok")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=lineno, col=col
    )
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_named_and_stararg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Keyword only star
    [Arguments]     ${arg1}  @{arg3}
    Log To Console     ${arg3}

*** Test Cases **
Normal test case
    Keyword only star    arg1   arg1=22   this is ok""",
    )

    lineno, col = doc.get_last_line_col()
    col -= len("1=22   this is ok")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=lineno, col=col
    )
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_name_star_even_with_eq(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "case4.robot",
        """
*** Keywords ***
Some Keyword
    [Arguments]    ${arg1}    ${arg2}    @{arg3}
    Log To Console      ${arg1} ${arg2} ${arg3}

*** Test Cases ***
Test case 1
    Some Keyword    val    another    foo    bar    some=1    anot""",
    )

    # Note: must match last because it's after a keyword arg.

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_star_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case_argspec", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Settings ***
Library  case_argspec.py
        
*** Test Cases ***
Check
    arg_with_starargs  arg1  arg2  in_star  in_star2""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_keyword_arg(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case_argspec", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Settings ***
Library  case_argspec.py
        
*** Test Cases ***
Check
    arg_with_starargs  arg1  arg2  in_star  in_star2  some_val=22""",
    )

    completion_context = CompletionContext(doc, workspace=workspace.ws)
    data_regression.check(signature_help(completion_context))


def test_signature_help_parameters_misleading_match_1(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.signature_help import signature_help

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """
*** Keywords ***
Keyword named and keyword
    [Arguments]     ${arg1}  @{arg3}  &{arg4}
    Log to console    22 @{arg3} &{arg4}

*** Test Cases **
Normal test case
    Keyword named and keyword    arg1=ok    arg3=keyword    arg4=arg4""",
    )

    lineno, col = doc.get_last_line_col()
    # We're actually matching the kwargs, not star args...
    col -= len("3=keyword    arg4=arg4")
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=lineno, col=col
    )
    data_regression.check(signature_help(completion_context))
