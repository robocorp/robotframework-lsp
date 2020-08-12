import pytest
import os


def test_dir_cache(tmpdir):
    from robocode_ls_core.cache import DirCache

    dir_cache = DirCache(str(tmpdir))
    dir_cache.store("key", 10)

    assert dir_cache.load("key", int) == 10
    with pytest.raises(KeyError):
        dir_cache.load("key", dict)

    filename = dir_cache._get_file_for_key("key")
    assert os.path.exists(filename)

    with open(filename, "w") as stream:
        stream.write("corrupted file")
    with pytest.raises(KeyError):
        assert dir_cache.load("key", int)

    dir_cache.store(("some key", 10), ("some", "val"))
    assert dir_cache.load(("some key", 10), list) == ["some", "val"]

    with pytest.raises(KeyError):
        assert dir_cache.load(("some key", 10), tuple)

    assert dir_cache.load(("some key", 10), list) == ["some", "val"]
    dir_cache.discard(("some key", 10))
