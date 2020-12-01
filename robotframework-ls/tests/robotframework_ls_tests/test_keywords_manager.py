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
    # i.e.: We now save it with a hash for relative files, so, it's something as:
    # os.path.join(libspec_manager.user_libspec_dir, "781b0814.libspec")
    assert not os.path.exists(libspec_file)
    dir_contents = [
        x
        for x in os.listdir(libspec_manager.user_libspec_dir)
        if x.endswith(".libspec")
    ]
    assert len(dir_contents) == 1
    libspec_manager.synchronize_internal_libspec_folders()
    assert sorted(libspec_manager.get_library_names()) == sorted(
        ["case1_library"] + list(robot_constants.STDLIBS)
    )

    assert get_library_info("invalid") is None

    library = get_library_info("case1_library")

    assert tuple(kw.name for kw in library.keywords) == (
        "Check With Multi Args",
        "Verify Another Model",
        "Verify Model",
    )

    for d in dir_contents:
        os.remove(os.path.join(libspec_manager.user_libspec_dir, d))
    libspec_manager.synchronize_internal_libspec_folders()
    assert sorted(libspec_manager.get_library_names()) == sorted(
        robot_constants.STDLIBS
    )

    assert get_library_info("case1_library", create=False) is None
    assert get_library_info("case1_library") is not None
