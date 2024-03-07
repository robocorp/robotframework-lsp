def test_variables_from_variables_file(tmpdir):
    from robotframework_ls.impl.variables_from_variable_file import (
        VariablesFromVariablesFileLoader,
    )

    filename = tmpdir.join("my.txt")
    filename.write_text(
        """
V_NAME = 'value'
V_NAME1 = 'value 1'
var2 = 'value var2'
""",
        encoding="utf-8",
    )

    v = VariablesFromVariablesFileLoader(str(filename))
    assert [x.variable_name for x in v.get_variables()] == ["V_NAME", "V_NAME1", "var2"]
