import pytest


class Item(object):
    def __init__(self, size):
        self.size = size


def test_lru():
    from robocorp_ls_core.cache import LRUCache

    cache: LRUCache[int, Item] = LRUCache(100, get_size=lambda a: a.size)
    assert round(cache.resize_to) == round(70)
    cache[1] = Item(45)

    # Here we'd go over the capacity (and that's ok for this class as we'll
    # resize to 70 and the sole item is below this).
    cache[2] = Item(40)

    assert len(cache) == 2
    assert cache.current_size_usage == 40 + 45

    # We'll still be over capacity and we'll have cycled only one element.
    cache[3] = Item(39)

    assert len(cache) == 2
    assert 1 not in cache
    assert cache.current_size_usage == 40 + 39

    # Make it the last accessed in the LRU (so it's kept instead of the one with
    # key == 3)
    assert cache[2].size == 40

    cache[4] = Item(38)
    assert len(cache) == 2
    assert 3 not in cache
    assert 2 in cache
    assert 4 in cache
    assert cache.current_size_usage == 40 + 38

    cache.clear()
    assert cache.current_size_usage == 0
    assert len(cache) == 0


def test_lru_unitary_size():
    from robocorp_ls_core.cache import LRUCache

    cache = LRUCache(3, 1)
    cache[1] = Item(1)
    assert len(cache) == 1

    cache[2] = Item(2)
    assert len(cache) == 2

    cache[3] = Item(3)
    assert len(cache) == 3

    cache[4] = Item(4)
    # It was resized to 1 and then item 4 was added
    assert len(cache) == 2

    assert cache.get(5) is None
    assert cache.current_size_usage == 2

    del cache[4]
    assert cache.current_size_usage == 1
    assert len(cache) == 1

    with pytest.raises(KeyError):
        del cache[4]

    assert 3 in cache

    item4 = cache[4] = Item(4)
    assert cache.pop(4) is item4

    with pytest.raises(KeyError):
        cache.pop(4)
    assert cache.pop(4, "foo") == "foo"
