import time


def test_workspace_memory_cache(tmpdir):
    from robocorp_ls_core.workspace import Workspace
    from robocorp_ls_core import uris
    from robocorp_ls_core.lsp import WorkspaceFolder
    from os.path import os

    root_uri = uris.from_fs_path(str(tmpdir))
    workspace_folders = [WorkspaceFolder(root_uri, os.path.basename(str(tmpdir)))]
    ws = Workspace(root_uri, workspace_folders)

    folders = list(ws.iter_folders())
    assert len(folders) == 1
    folder = folders[0]
    vs = folder._obtain_vs()
    assert vs.cache_misses == 0

    assert list(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == []
    assert vs.cache_misses == 1
    # If the change is too fast the mtime may end up being the same...
    time.sleep(0.01)

    f = tmpdir.join("my.txt")
    f.write_text("foo", "utf-8")

    assert list(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == [
        uris.from_fs_path(str(f))
    ]
    assert vs.cache_misses == 2

    # If the change is too fast the mtime may end up being the same...
    time.sleep(0.01)

    dir1 = tmpdir.join("dir1")
    dir1.mkdir()

    f2 = dir1.join("my.py")
    f2.write_text("foo", "utf-8")

    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f)),
        uris.from_fs_path(str(f2)),
    }

    # Cache miss went += 2 because 2 folders were changed.
    assert vs.cache_misses == 4

    # No cache misses now
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f)),
        uris.from_fs_path(str(f2)),
    }
    assert vs.cache_misses == 4

    # If the change is too fast the mtime may end up being the same...
    time.sleep(0.01)
    f2.remove()

    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f))
    }
    assert vs.cache_misses == 5

    # No cache miss now
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f))
    }
    assert vs.cache_misses == 5
