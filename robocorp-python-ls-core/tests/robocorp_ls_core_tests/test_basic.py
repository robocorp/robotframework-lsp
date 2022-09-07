def test_isinstance_name():
    from robocorp_ls_core.basic import isinstance_name

    class A(object):
        pass

    class B(A):
        pass

    class C(B):
        pass

    for _ in range(2):
        assert isinstance_name(B(), "B")
        assert isinstance_name(B(), "A")
        assert isinstance_name(B(), "object")

        assert isinstance_name(B(), ("A", "C"))

        assert not isinstance_name(B(), "C")
        assert not isinstance_name(B(), ("C", "D"))


def test_notify_about_import(tmpdir):
    from robocorp_ls_core.basic import notify_about_import
    import sys
    import io
    from robocorp_ls_core.robotframework_log import configure_logger

    tmpdir.join("my_test_notify_about_import.py").write_text("a = 10", "utf-8")
    path = sys.path[:]
    sys.path.append(str(tmpdir))
    try:
        s = io.StringIO()
        with configure_logger("", 1, s):
            with notify_about_import("my_test_notify_about_import"):
                import my_test_notify_about_import  # type: ignore  #noqa

                assert my_test_notify_about_import.a == 10
        assert (
            "import my_test_notify_about_import  # type: ignore  #noqa" in s.getvalue()
        )
        assert (
            "'my_test_notify_about_import' should not be imported in this process"
            in s.getvalue()
        )
    finally:
        sys.path = path
