def test_keywords_manager(tmpdir, workspace):
    from robotframework_ls.impl.libspec_manager import LibspecManager
    import os
    import pytest

    user_home = tmpdir.join("user_home")
    libspec_manager = LibspecManager(user_home=str(user_home))
    try:
        workspace.set_root("case1", libspec_manager=libspec_manager)

        libspec_manager.create_libspec("case1_library")
        libspec_file = os.path.join(
            libspec_manager.libspec_dir, "case1_library.libspec"
        )
        assert os.path.exists(libspec_file)
        libspec_manager.synchronize()
        assert libspec_manager.get_library_names() == ["case1_library"]

        with pytest.raises(KeyError):
            libspec_manager.get_library_info("invalid")

        library = libspec_manager.get_library_info("case1_library")

        assert tuple(kw.name for kw in library.keywords) == (
            "Verify Another Model",
            "Verify Model",
        )

        os.remove(libspec_file)
        libspec_manager.synchronize()
        assert libspec_manager.get_library_names() == []
        with pytest.raises(KeyError):
            libspec_manager.get_library_info("case1_library", create=False)
        assert libspec_manager.get_library_info("case1_library") is not None
    finally:
        libspec_manager.dispose()
