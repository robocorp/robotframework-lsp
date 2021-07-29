import pytest


@pytest.fixture(params=["watchdog", "fsnotify"])
def remote_fs_observer(request):
    from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver

    backend = request.param
    remote_fsobserver = RemoteFSObserver(backend, None)
    try:
        port = remote_fsobserver.start_server()
        assert port
        yield remote_fsobserver
    finally:
        remote_fsobserver.dispose()


def test_remote_fs_observer(remote_fs_observer, tmpdir):
    from robocorp_ls_core import watchdog_wrapper
    from robocorp_ls_core.watchdog_wrapper import PathInfo
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition
    from robocorp_ls_core.watchdog_wrapper import IFSObserver

    tmpdir.join("dir_not_rec").mkdir()
    tmpdir.join("dir_rec").mkdir()

    found = []

    def on_change(filepath, *args):
        found.append(filepath)
        assert args == ("foo", "bar")

    notifier = watchdog_wrapper.create_notifier(on_change, timeout=0.1)
    observer: IFSObserver = remote_fs_observer

    watch = observer.notify_on_any_change(
        [
            PathInfo(tmpdir.join("dir_not_rec"), False),
            PathInfo(tmpdir.join("dir_rec"), True),
        ],
        notifier.on_change,
        call_args=("foo", "bar"),
    )

    try:
        tmpdir.join("dir_not_rec").join("mya.txt").write("foo")
        tmpdir.join("dir_not_rec").join("mya.libspec").write("foo")

        tmpdir.join("dir_rec").join("myb.txt").write("foo")
        tmpdir.join("dir_rec").join("myb.libspec").write("foo")

        def collect_basenames():
            import os.path

            basenames = [os.path.basename(x) for x in found]
            return set(basenames)

        def check1():
            expected = {"myb.txt", "mya.libspec", "myb.libspec", "mya.txt"}
            return collect_basenames().issuperset(expected)

        wait_for_test_condition(
            check1, msg=lambda: f"Basenames found: {collect_basenames()}"
        )

    finally:
        watch.stop_tracking()
        notifier.dispose()
        observer.dispose()


def test_glob_matches_path():
    from robocorp_ls_core.load_ignored_dirs import glob_matches_path
    import sys

    # Linux
    for sep, altsep in (("\\", "/"), ("/", None)):

        def build(path):
            if sep == "/":
                return path
            else:
                return ("c:" + path).replace("/", "\\")

        assert glob_matches_path(build("/a"), r"*", sep, altsep)

        assert not glob_matches_path(
            build("/a/b/c/some.py"), "/a/**/c/so?.py", sep, altsep
        )

        assert glob_matches_path("/a/b/c", "/a/b/*")
        assert not glob_matches_path("/a/b", "/*")
        assert glob_matches_path("/a/b", "/*/b")
        assert glob_matches_path("/a/b", "**/*")
        assert not glob_matches_path("/a/b", "**/a")

        assert glob_matches_path(build("/a/b/c/d"), "**/d", sep, altsep)
        assert not glob_matches_path(build("/a/b/c/d"), "**/c", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "**/c/d", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "**/b/c/d", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "/*/b/*/d", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "**/c/*", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "/a/**/c/*", sep, altsep)

        # I.e. directories are expected to end with '/', so, it'll match
        # something as **/directory/**
        assert glob_matches_path(build("/a/b/c/"), "**/c/**", sep, altsep)
        assert glob_matches_path(build("/a/b/c/"), "**/c/", sep, altsep)
        # But not something as **/directory (that'd be a file match).
        assert not glob_matches_path(build("/a/b/c/"), "**/c", sep, altsep)
        assert not glob_matches_path(build("/a/b/c"), "**/c/", sep, altsep)

        assert glob_matches_path(build("/a/b/c/d.py"), "/a/**/c/*", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d.py"), "/a/**/c/*.py", sep, altsep)
        assert glob_matches_path(build("/a/b/c/some.py"), "/a/**/c/so*.py", sep, altsep)
        assert glob_matches_path(
            build("/a/b/c/some.py"), "/a/**/c/som?.py", sep, altsep
        )
        assert glob_matches_path(build("/a/b/c/d"), "/**", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d"), "/**/d", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d.py"), "/**/*.py", sep, altsep)
        assert glob_matches_path(build("/a/b/c/d.py"), "**/c/*.py", sep, altsep)

        if sys.platform == "win32":
            assert glob_matches_path(build("/a/b/c/d.py"), "**/C/*.py", sep, altsep)
            assert glob_matches_path(build("/a/b/C/d.py"), "**/c/*.py", sep, altsep)

        # Expected not to match.
        assert not glob_matches_path(build("/a/b/c/d"), "/**/d.py", sep, altsep)
        assert not glob_matches_path(build("/a/b/c/d.pyx"), "/a/**/c/*.py", sep, altsep)
        assert not glob_matches_path(build("/a/b/c/d"), "/*/d", sep, altsep)

        if sep == "/":
            assert not glob_matches_path(
                build("/a/b/c/d"), r"**\d", sep, altsep
            )  # Match with \ doesn't work on linux...
            assert not glob_matches_path(
                build("/a/b/c/d"), r"c:\**\d", sep, altsep
            )  # Match with drive doesn't work on linux...
        else:
            # Works in Windows.
            assert glob_matches_path(build("/a/b/c/d"), r"**\d", sep, altsep)
            assert glob_matches_path(build("/a/b/c/d"), r"c:\**\d", sep, altsep)

        # Corner cases
        assert not glob_matches_path(build("/"), r"", sep, altsep)
        assert glob_matches_path(build(""), r"", sep, altsep)
        assert not glob_matches_path(build(""), r"**", sep, altsep)
        assert glob_matches_path(build("/"), r"**", sep, altsep)
        assert glob_matches_path(build("/"), r"*", sep, altsep)


def test_create_accept_directory_callable():
    from robocorp_ls_core.load_ignored_dirs import create_accept_directory_callable

    accept_directory = create_accept_directory_callable("")
    assert not accept_directory("/my/node_modules")
    assert accept_directory("/my")

    accept_directory = create_accept_directory_callable('["**/bazel_out/**"]')
    assert accept_directory("/my/foobar")
    assert not accept_directory(
        "/Users/ichamberlain/Documents/workspace/bazel_out/execroot/my_org/bazel_out/execroot/my_org/bazel_out/execroot/my_org"
    )
