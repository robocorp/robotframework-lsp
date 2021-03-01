import pytest


@pytest.fixture
def small_vs_sleep():
    from robocorp_ls_core.workspace import _VirtualFSThread

    original = _VirtualFSThread.SLEEP_AMONG_SCANS
    _VirtualFSThread.SLEEP_AMONG_SCANS = 0.05
    yield
    _VirtualFSThread.SLEEP_AMONG_SCANS = original


def test_workspace_memory_cache(tmpdir, small_vs_sleep):
    from robocorp_ls_core.workspace import Workspace
    from robocorp_ls_core import uris
    from robocorp_ls_core.lsp import WorkspaceFolder
    from os.path import os

    root_uri = uris.from_fs_path(str(tmpdir))
    workspace_folders = [WorkspaceFolder(root_uri, os.path.basename(str(tmpdir)))]
    ws = Workspace(root_uri, workspace_folders, track_file_extensions=(".py", ".txt"))

    folders = list(ws.iter_folders())
    assert len(folders) == 1
    folder = folders[0]
    vs = folder._vs
    vs.wait_for_check_done(5)

    assert list(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == []
    # If the change is too fast the mtime may end up being the same...

    f = tmpdir.join("my.txt")
    f.write_text("foo", "utf-8")
    vs.wait_for_check_done(5)

    assert list(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == [
        uris.from_fs_path(str(f))
    ]

    dir1 = tmpdir.join("dir1")
    dir1.mkdir()

    f2 = dir1.join("my.py")
    f2.write_text("foo", "utf-8")

    vs.wait_for_check_done(5)
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f)),
        uris.from_fs_path(str(f2)),
    }

    vs.wait_for_check_done(5)
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f)),
        uris.from_fs_path(str(f2)),
    }

    # If the change is too fast the mtime may end up being the same...
    f2.remove()

    vs.wait_for_check_done(5)
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f))
    }

    vs.wait_for_check_done(5)
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == {
        uris.from_fs_path(str(f))
    }

    ws.remove_folder(root_uri)
    assert set(ws.iter_all_doc_uris_in_workspace((".py", ".txt"))) == set()
    vs._virtual_fsthread.join(0.5)
    assert not vs._virtual_fsthread.is_alive()
