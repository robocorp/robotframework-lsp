def test_isinstance_name():
    from robocode_ls_core.basic import isinstance_name

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
