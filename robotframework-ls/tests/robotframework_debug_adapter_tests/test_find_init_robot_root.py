def test_find_init_robot_root(tmpdir):
    from robotframework_debug_adapter.launch_process import find_init_robot_root

    dira = tmpdir.join("dira")
    dira.mkdir()

    sub1 = dira.join("sub1")
    sub1.mkdir()

    sub2 = sub1.join("sub2")
    sub2.mkdir()

    sub2_init = sub2.join("__init__.robot")
    sub2_init.write_text("", encoding="utf-8")

    some_robot = sub2.join("some.robot")
    some_robot.write_text("", encoding="utf-8")

    assert find_init_robot_root(str(some_robot), str(dira)) == str(sub2)
    assert find_init_robot_root(str(some_robot), "") == str(sub2)

    dira_init = dira.join("__init__.robot")
    dira_init.write_text("", encoding="utf-8")
    assert find_init_robot_root(str(some_robot), str(dira)) == str(dira)
    assert find_init_robot_root(str(some_robot), "") == str(dira)

    sub2_init.remove()
    dira_init.remove()

    assert find_init_robot_root(str(some_robot), str(dira)) is None
    assert find_init_robot_root(str(some_robot), "") is None
