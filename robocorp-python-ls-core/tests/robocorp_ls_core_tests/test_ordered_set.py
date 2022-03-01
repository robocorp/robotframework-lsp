def test_ordered_set():
    from robocorp_ls_core.ordered_set import OrderedSet

    ordered_set = OrderedSet()
    assert not ordered_set
    ordered_set.add(1)
    assert ordered_set
    ordered_set.add(2)
    ordered_set.add(3)
    ordered_set.add(4)
    ordered_set.add(5)
    assert list(ordered_set) == [1, 2, 3, 4, 5]

    ordered_set.discard(3)
    assert list(ordered_set) == [1, 2, 4, 5]

    ordered_set.add(3)
    assert list(ordered_set) == [1, 2, 4, 5, 3]

    # i.e.: already there (order unchanged).
    for i in range(1, 6):
        ordered_set.add(i)
    assert list(ordered_set) == [1, 2, 4, 5, 3]
    assert len(ordered_set) == 5
    assert repr(ordered_set) == "OrderedSet([1, 2, 4, 5, 3])"
    assert str(ordered_set) == "OrderedSet([1, 2, 4, 5, 3])"

    assert 2 in ordered_set
    assert 10 not in ordered_set
