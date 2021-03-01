def test_virtual_fs(tmpdir):
    from robocorp_ls_core.workspace import _VirtualFS

    root = str(tmpdir)
    virtual_fs = _VirtualFS(root, (".py", ".robot"))
    try:
        directories = set()
        extensions = (".py",)  # We can later use just a subset
        assert not list(virtual_fs.scandir(root, directories, extensions))
    finally:
        virtual_fs.dispose()
