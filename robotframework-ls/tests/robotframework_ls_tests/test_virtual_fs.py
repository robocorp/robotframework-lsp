def test_virtual_fs(tmpdir, remote_fs_observer):
    from robocorp_ls_core.workspace import _VirtualFS
    from robocorp_ls_core.watchdog_wrapper import IFSObserver
    import os

    root = str(tmpdir)
    fs_observer: IFSObserver = remote_fs_observer
    virtual_fs = _VirtualFS(root, (".py", ".robot"), fs_observer=fs_observer)
    try:
        extensions = (".py",)  # We can later use just a subset
        assert not list(virtual_fs._iter_all_doc_uris(extensions))

        def check_found_py(expected_basenames):
            from robocorp_ls_core.basic import wait_for_condition

            def check():
                found = list(virtual_fs._iter_all_doc_uris(extensions))
                return set([os.path.basename(x) for x in found]) == set(
                    expected_basenames
                )

            wait_for_condition(check)

        # Create a dir1 and my.py
        dir1 = tmpdir.join("dir1")
        dir1.mkdir()
        dir1.join("my.py").write_text("foo", encoding="utf-8")
        check_found_py(["my.py"])

        # Create a dir2 and my2.py
        dir2 = tmpdir.join("dir2")
        dir2.mkdir()
        dir2.join("my2.py").write_text("foo", encoding="utf-8")
        check_found_py(["my.py", "my2.py"])

        # Remove dir1 and see that it no longer appears.
        dir1.join("my.py").remove()
        dir1.remove()
        check_found_py(["my2.py"])

        # Create a dir3/dir4/dir5/my5.py
        dir3 = tmpdir.join("dir3")
        dir3.mkdir()
        dir4 = dir3.join("dir4")
        dir4.mkdir()
        dir5 = dir4.join("dir5")
        dir5.mkdir()
        dir5.join("my5.py").write_text("foo", encoding="utf-8")
        check_found_py(["my2.py", "my5.py"])

    finally:
        virtual_fs.dispose()
        fs_observer.dispose()
