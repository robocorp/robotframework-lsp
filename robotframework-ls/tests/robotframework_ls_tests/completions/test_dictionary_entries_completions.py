def test_dictionary_entries_completions_1(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
&{Person}   First name=John   Last name=Smith

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[First]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)


def test_dictionary_entries_completions_2(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
&{Person}         Address=&{home_address}
&{home_address}   City=Somewhere   Zip Code=12345

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[Address][Zip]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)


def test_dictionary_entries_completions_3(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
&{Person}         Address=&{home_address}
&{home_address}   City=&{Finnland}[Cities]   Zip Code=12345
&{Finnland}       Cities=&{kaupungeista}
&{kaupungeista}   Home of Aalto University=Espoo

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[Address][City][Home of]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)


def test_dictionary_entries_completions_4(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")
    doc.source = """
*** Variables ***
&{Some Person}         Address=&{home_address}
&{home_address}   City=&{Finnland}[Cities]   Zip Code=12345
&{Finnland}       Cities=&{kaupungeista}
&{kaupungeista}   Home of Aalto University=Espoo

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Some Person}[Address][City][Home of]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)