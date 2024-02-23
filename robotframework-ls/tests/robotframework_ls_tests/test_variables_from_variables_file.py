def test_variables_from_variables_file(workspace, tmpdir):
    import typing
    from robotframework_ls.impl.variables_from_variable_file import (
        VariablesFromVariablesFileLoader,
    )
    from robotframework_ls.impl.protocols import (
        IRobotDocument,
    )
    from robocorp_ls_core import uris

    workspace.set_root(str(tmpdir))
    filename = tmpdir / "my.py"
    filename.write_text(
        """
V_NAME='value'
V_NAME1='value 1'
var2='value var2'
""",
        encoding="utf-8",
    )

    doc_uri = uris.from_fs_path(str(filename))
    resource_doc = workspace.ws.get_document(doc_uri, accept_from_file=True)
    robot_doc = typing.cast(IRobotDocument, resource_doc)
    v = VariablesFromVariablesFileLoader(str(filename), robot_doc)
    assert [x.variable_name for x in v.get_variables()] == ["V_NAME", "V_NAME1", "var2"]
