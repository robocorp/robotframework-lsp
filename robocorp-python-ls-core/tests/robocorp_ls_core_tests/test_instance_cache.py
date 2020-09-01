import itertools
from robocorp_ls_core.cache import instance_cache


def test_instance_cache():
    class MyClass(object):
        def __init__(self, initial=0):
            self._count = itertools.count(initial)

        @instance_cache
        def cache_this(self):
            return next(self._count)

    c = MyClass(0)
    assert c.cache_this() == 0
    assert c.cache_this() == 0
    c.cache_this.cache_clear(c)
    assert c.cache_this() == 1

    c2 = MyClass(22)
    assert c.cache_this() == 1
    assert c2.cache_this() == 22
    assert c2.cache_this() == 22


def test_instance_cache_args():
    class MyClass(object):
        def __init__(self, initial=0):
            self._count = itertools.count(initial)

        @instance_cache
        def cache_this(self, arg):
            return next(self._count), arg

    c = MyClass(0)
    assert c.cache_this(1) == (0, 1)
    assert c.cache_this(1) == (0, 1)
    assert c.cache_this(2) == (1, 2)
    c.cache_this.cache_clear(c)
    assert c.cache_this(1) == (2, 1)
