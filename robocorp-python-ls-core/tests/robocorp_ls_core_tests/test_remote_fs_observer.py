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
