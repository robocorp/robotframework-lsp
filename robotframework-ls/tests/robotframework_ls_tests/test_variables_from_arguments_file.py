def test_variables_from_arguments_file(tmpdir):
    from robotframework_ls.impl.variables_from_arguments_file import (
        VariablesFromArgumentsFileLoader,
    )

    filename = tmpdir.join("my.txt")
    filename.write_text(
        """
-v V_NAME:value
--variable V_NAME1:value 1
--variable var2:value var2
""",
        encoding="utf-8",
    )

    v = VariablesFromArgumentsFileLoader(str(filename))
    assert [x.variable_name for x in v.get_variables()] == ["V_NAME", "V_NAME1", "var2"]
