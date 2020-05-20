def test_get_ast():
    from robotframework_ls.impl.robot_workspace import RobotDocument

    d = RobotDocument(uri="unkwown", source="*** Settings ***")
    ast = d.get_ast()
    assert ast is not None
    assert d.get_ast() is ast  # Check cache

    d.source = "*** Foobar"
    assert d.get_ast() is not ast
