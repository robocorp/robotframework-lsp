import os


def test_code_lens_run_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens_runs
    from robotframework_ls.impl.code_lens import code_lens_resolve

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """

*** Test Cases ***
Some Test
    [Documentation]      Docs
    
*** Task ***
Some Task
    [Documentation]      Docs
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens_runs(completion_context)
    check_data_regression(data_regression, found)
    for c in found:
        # i.e.: don't change anything here
        assert code_lens_resolve(completion_context, c) == c


def check_data_regression(data_regression, found, basename=None):
    import copy

    # For checking the test we need to make the uri/path the same among runs.
    found = copy.deepcopy(found)  # we don't want to change the initial data
    for c in found:
        command = c["command"]
        if command:
            arguments = command["arguments"]
            if arguments:
                arg0 = arguments[0]
                uri = arg0.get("uri")
                if uri:
                    arg0["uri"] = uri.split("/")[-1]

                path = arg0.get("path")
                if path:
                    arg0["path"] = os.path.basename(path)

        data = c.get("data")
        if data:
            uri = data.get("uri")
            if uri:
                data["uri"] = uri.split("/")[-1]
    data_regression.check(found, basename=basename)


def test_code_lens_scratchpad_basic(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.code_lens import code_lens_scratchpad
    from robotframework_ls.impl.code_lens import code_lens_resolve

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case4.robot")
    doc.source = """

*** Settings ***
Library     my_lib.py
Resource    my_resource.robot

*** Test Cases ***
Some Test
    [Documentation]      Docs
    Some Keyword
    
*** Keyword ***
Some Keyword
    Log    Something    console=True
"""

    completion_context = CompletionContext(doc, workspace=workspace.ws)

    found = code_lens_scratchpad(completion_context)
    check_data_regression(
        data_regression,
        found,
        basename="test_code_lens_scratchpad_basic_before_resolve",
    )

    new_found = [code_lens_resolve(completion_context, c) for c in found]
    check_data_regression(
        data_regression,
        new_found,
        basename="test_code_lens_scratchpad_basic_after_resolve",
    )
