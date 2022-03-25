def test_dictionary_entries_completions_1(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


def test_dictionary_entries_completions_1_a(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
&{Person}   First name=John   Last name=Smith

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)


def test_dictionary_entries_completions_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


def test_dictionary_entries_completions_2_a(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
&{Person}         Address=&{home_address}
&{home_address}   City=Somewhere   Zip Code=12345

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[Address][]"""
    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions)


def test_dictionary_entries_completions_3(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


def test_dictionary_entries_completions_4(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
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


def test_dictionary_entries_completions_4_in_2_files(
    workspace, libspec_manager, data_regression
):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)

    doc = workspace.put_doc(
        "case2.robot",
        """
*** Settings ***
Resource    case2a.resource
*** Variables ***
&{Some Person}         Address=&{home_address}
&{Finnland}       Cities=&{kaupungeista}
&{kaupungeista}   Home of Aalto University=Espoo
*** Test Cases ***
Dictionary Variable
    Log to Console    ${Some Person}[Address][City][Home of]""",
    )

    workspace.put_doc(
        "case2a.resource",
        """
*** Variables ***
&{home_address}   City=&{Finnland}[Cities]   Zip Code=12345
""",
    )

    line, col = doc.get_last_line_col()
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws, line=line, col=col - len("]"))
    )
    data_regression.check(completions, basename="test_dictionary_entries_completions_4")


def test_dictionary_entries_completions_5(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl import dictionary_completions

    workspace.set_root("case2", libspec_manager=libspec_manager)
    doc = workspace.put_doc("case2.robot")
    doc.source = """
*** Variables ***
&{Some Person}         Address=&{home_address}
&{home_address}   City=&{Finnland}[Cities]   Zip Code=12345
&{Finnland}       Cities=&{kaupungeista}
&{kaupungeista}   Home of Aalto University=Espoo

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Some Per"""
    completions = dictionary_completions.complete(
        CompletionContext(doc, workspace=workspace.ws)
    )
    # ie.: empty (just checking that it doesn't crash).
    data_regression.check(completions)
