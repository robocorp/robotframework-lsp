def test_variables_from_variables_file(tmpdir):
    import typing
    from robotframework_ls.impl.variables_from_variable_file import (
        VariablesFromVariablesFileLoader,
    )
    from robotframework_ls.impl.protocols import (
        IRobotDocument,
    )
    from robocorp_ls_core import uris
    from robocorp_ls_core.watchdog_wrapper import create_observer
    from robocorp_ls_core.workspace import Workspace

    filename = tmpdir.join("my.txt")
    filename.write_text(
        """
V_NAME='value'
V_NAME1='value 1'
var2='value var2'
""",
        encoding="utf-8",
    )

    ws = Workspace(str(filename), create_observer("dummy", None))

    doc_uri = uris.from_fs_path(str(filename))
    resource_doc = ws.get_document(doc_uri, accept_from_file=True)
    robot_doc = typing.cast(IRobotDocument, resource_doc)
    v = VariablesFromVariablesFileLoader(str(filename), robot_doc)
    assert [x.variable_name for x in v.get_variables()] == ["V_NAME", "V_NAME1", "var2"]
