from robocorp_ls_core.lsp import SelectionRangeTypedDict, RangeTypedDict, Range


def _check_not_same_and_inside(child: RangeTypedDict, parent: RangeTypedDict):
    c = Range.create_from_range_typed_dict(child)
    p = Range.create_from_range_typed_dict(parent)
    assert c != p, f"{c} is equal to {p}"
    assert c.is_inside(p), f"{c} should be inside {p}"


def check_parent_ranges(r: SelectionRangeTypedDict):
    parent = r.get("parent")
    if parent is not None:
        _check_not_same_and_inside(r["range"], parent["range"])
        check_parent_ranges(parent)


def test_selection_range_basic(workspace, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4")
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Collections.Append to list    foo
    Append to list    foo""",
    )

    line, _col = doc.get_last_line_col()
    col = 5

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)


def test_selection_range_no_dupes(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Collections.Append to list    foo
    Append to list""",
    )

    line, _col = doc.get_last_line_col()
    col = 5

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)


def test_selection_range_variables(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    Collections.Append to list    foo
    ${var a}=   Append to list""",
    )

    line, _col = doc.get_last_line_col()
    col = 6

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)


def test_selection_range_variables_2(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    ${var a['bar']}=    Evaluate    'bar'""",
    )

    line, _col = doc.get_last_line_col()
    col = 6

    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)


def test_selection_range_variables_3(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    ${var a['bar']}=    Evaluate    'bar'""",
    )

    line, _col = doc.get_last_line_col()
    col = 14
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)


def test_selection_range_on_empty_space(workspace, libspec_manager, data_regression):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.selection_range import selection_range

    workspace.set_root("case4", libspec_manager=libspec_manager)
    doc = workspace.put_doc(
        "my.robot",
        """*** Settings ***
Library    Collections

*** Test Cases ***
Test case 1
    ${var a['bar']}=    Evaluate    'bar'""",
    )

    line, _col = doc.get_last_line_col()
    col = 1
    completion_context = CompletionContext(
        doc, workspace=workspace.ws, line=line, col=col
    )
    positions = [{"line": line, "character": col}]
    result = selection_range(completion_context, positions=positions)
    assert len(result) == 1
    for r in result:
        check_parent_ranges(r)
    data_regression.check(result)
