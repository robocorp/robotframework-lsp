def test_libspec_info(libspec_manager, tmpdir):
    from robotframework_ls.impl.robot_specbuilder import LibraryDoc
    from robotframework_ls.impl.robot_specbuilder import KeywordDoc

    assert "BuiltIn" in libspec_manager.get_library_names()
    lib_info = libspec_manager.get_library_info("BuiltIn", create=False)
    assert isinstance(lib_info, LibraryDoc)
    assert lib_info.source is not None
    assert lib_info.source.endswith("BuiltIn.py")
    for keyword in lib_info.keywords:
        assert isinstance(keyword, KeywordDoc)
        assert keyword.lineno > 0


def test_libspec_manager_caches(libspec_manager, workspace_dir):
    from robocorp_ls_core import uris
    from os.path import os
    from robotframework_ls_tests.fixtures import LIBSPEC_1
    from robotframework_ls_tests.fixtures import LIBSPEC_2
    from robotframework_ls_tests.fixtures import LIBSPEC_2_A
    import time
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    workspace_dir_a = os.path.join(workspace_dir, "workspace_dir_a")
    os.makedirs(workspace_dir_a)
    with open(os.path.join(workspace_dir_a, "my.libspec"), "w") as stream:
        stream.write(LIBSPEC_1)
    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    libspec_manager.remove_workspace_folder(uris.from_fs_path(workspace_dir_a))
    library_info = libspec_manager.get_library_info("case1_library", create=False)
    if library_info is not None:
        raise AssertionError(
            "Expected: %s to be None after removing %s"
            % (library_info, uris.from_fs_path(workspace_dir_a))
        )

    libspec_manager.add_workspace_folder(uris.from_fs_path(workspace_dir_a))
    assert libspec_manager.get_library_info("case1_library", create=False) is not None

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1.1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2)

    def check_spec_found():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        return library_info is not None

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_found, sleep=1 / 5.0)

    library_info = libspec_manager.get_library_info("case2_library", create=False)
    assert set(x.name for x in library_info.keywords) == set(
        ["Case 2 Verify Another Model", "Case 2 Verify Model"]
    )

    # Give a timeout so that the next write will have at least 1 second
    # difference (1s is the minimum for poll to work).
    time.sleep(1)
    with open(os.path.join(workspace_dir_a, "my2.libspec"), "w") as stream:
        stream.write(LIBSPEC_2_A)

    def check_spec_2_a():
        library_info = libspec_manager.get_library_info("case2_library", create=False)
        if library_info:
            return set(x.name for x in library_info.keywords) == set(
                ["Case 2 A Verify Another Model", "Case 2 A Verify Model"]
            )

    # Updating is done in a thread.
    wait_for_test_condition(check_spec_2_a, sleep=1 / 5.0)
