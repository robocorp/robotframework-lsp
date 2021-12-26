import pytest

CASE_TEMPLATE = """
*** Keywords ***
My Equal Redefined
    [Arguments]         ${arg1}     ${arg2}
    Should Be Equal     ${arg1}     ${arg2}

*** Task ***
Some task
    My Equal Redefined"""


@pytest.fixture
def check(workspace, libspec_manager, data_regression):
    def check_func(source, col_delta=0, expect_completions=True, line_col=None):
        from robotframework_ls.impl.completion_context import CompletionContext
        from robotframework_ls.impl import keyword_parameter_completions

        workspace.set_root("case2", libspec_manager=libspec_manager)
        doc = workspace.put_doc("case2.robot")
        doc.source = source

        if line_col is not None:
            line, col = line_col
        else:
            line, col = doc.get_last_line_col()
            col += col_delta

        completions = keyword_parameter_completions.complete(
            CompletionContext(doc, workspace=workspace.ws, line=line, col=col)
        )

        if expect_completions:
            data_regression.check(completions)
        else:
            assert not completions

    return check_func


def test_keyword_completions_params_basic(check):
    check(CASE_TEMPLATE + "    ")


def test_keyword_completions_params_complete_existing_simple(check):
    check(CASE_TEMPLATE + "    ar")


def test_keyword_completions_params_complete_existing_2nd(check):
    check(CASE_TEMPLATE + "    arg2=10    ar")


def test_keyword_completions_params_complete_existing_no_chars(check):
    check(CASE_TEMPLATE + "    arg2=10    ")


def test_keyword_completions_params_complete_existing_no_chars_with_empty_new_line_after(
    check,
):
    from robocorp_ls_core.workspace import Document

    base = CASE_TEMPLATE + "    arg2=10    "
    doc = Document("", base)
    line, col = doc.get_last_line_col()
    check(base + "\n    ", line_col=(line, col))


def test_keyword_completions_params_dont_complete(check):
    # in keyword name
    check(CASE_TEMPLATE + "", expect_completions=False)

    # in the middle of the parameter
    check(CASE_TEMPLATE + "    ar", col_delta=-1, expect_completions=False)

    # in the middle of the word
    check(CASE_TEMPLATE + "    ar", col_delta=-2, expect_completions=False)

    # in parameter assign part
    check(CASE_TEMPLATE + "    ar=", expect_completions=False)

    # in parameter assign part
    check(CASE_TEMPLATE + "    ar=a", expect_completions=False)
