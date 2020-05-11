def test_keywords_manager(workspace, libspec_manager):
    import os
    from robotframework_ls.impl import robot_constants

    workspace.set_root("case1", libspec_manager=libspec_manager)
    doc = workspace.get_doc("case1.robot")

    def get_library_info(*args, **kwargs):
        kwargs["current_doc_uri"] = doc.uri
        return libspec_manager.get_library_info(*args, **kwargs)

    assert get_library_info("case1_library") is not None
    libspec_file = os.path.join(
        libspec_manager.user_libspec_dir, "case1_library.libspec"
    )
    assert os.path.exists(libspec_file)
    libspec_manager.synchronize_internal_libspec_folders()
    assert sorted(libspec_manager.get_library_names()) == sorted(
        ["case1_library"] + list(robot_constants.STDLIBS)
    )

    assert get_library_info("invalid") is None

    library = get_library_info("case1_library")

    assert tuple(kw.name for kw in library.keywords) == (
        "Verify Another Model",
        "Verify Model",
    )

    os.remove(libspec_file)
    libspec_manager.synchronize_internal_libspec_folders()
    assert sorted(libspec_manager.get_library_names()) == sorted(
        robot_constants.STDLIBS
    )

    assert get_library_info("case1_library", create=False) is None
    assert get_library_info("case1_library") is not None
