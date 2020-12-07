import time
import pytest
import sys


@pytest.mark.skipif(sys.platform != "darwin", reason="Mac OS only test.")
def test_watchdog_macos():
    # Make sure that the binary deps are distributed in Mac OS.

    import os.path
    from robocorp_ls_core import watchdog_wrapper

    watchdog_wrapper._import_watchdog()
    import watchdog

    assert os.path.exists(
        os.path.join(
            watchdog_wrapper._get_watchdog_lib_dir(),
            "_watchdog_fsevents.cpython-37m-darwin.so",
        )
    )
    assert os.path.exists(
        os.path.join(
            watchdog_wrapper._get_watchdog_lib_dir(),
            "_watchdog_fsevents.cpython-38-darwin.so",
        )
    )
    assert os.path.exists(
        os.path.join(
            watchdog_wrapper._get_watchdog_lib_dir(),
            "_watchdog_fsevents.cpython-39-darwin.so",
        )
    )

    try:
        from watchdog.observers import fsevents  # noqa
    except:
        sys_path = "\n    ".join(sorted(sys.path))
        raise AssertionError(
            f"Could not import _watchdog_fsevents.\nWatchdog found: {watchdog}\n"
            f"sys.path:\n{sys_path}\n"
            f"watchdog_dir: {watchdog_wrapper._get_watchdog_lib_dir()}\n"
        )


def test_watchdog_all(tmpdir):
    from robocorp_ls_core import watchdog_wrapper
    from robocorp_ls_core.watchdog_wrapper import PathInfo
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    tmpdir.join("dir_not_rec").mkdir()
    tmpdir.join("dir_rec").mkdir()

    found = []

    def on_change(filepath, *args):
        found.append(filepath)
        assert args == ("foo", "bar")

    notifier = watchdog_wrapper.create_notifier(on_change, timeout=0.1)
    observer = watchdog_wrapper.create_observer()

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


def test_watchdog_extensions(tmpdir):
    from robocorp_ls_core import watchdog_wrapper
    from robocorp_ls_core.watchdog_wrapper import PathInfo
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition

    tmpdir.join("dir_not_rec").mkdir()
    tmpdir.join("dir_rec").mkdir()

    found = []

    def on_change(filepath, *args):
        found.append(filepath)
        assert args == ("foo", "bar")

    notifier = watchdog_wrapper.create_notifier(on_change, timeout=0.1)
    observer = watchdog_wrapper.create_observer()

    watch = observer.notify_on_extensions_change(
        [
            PathInfo(tmpdir.join("dir_not_rec"), False),
            PathInfo(tmpdir.join("dir_rec"), True),
        ],
        ["libspec"],
        notifier.on_change,
        call_args=("foo", "bar"),
    )

    try:
        tmpdir.join("my.txt").write("foo")
        tmpdir.join("my.libspec").write("foo")

        tmpdir.join("dir_not_rec").join("mya.txt").write("foo")
        tmpdir.join("dir_not_rec").join("mya.libspec").write("foo")

        tmpdir.join("dir_rec").join("myb.txt").write("foo")
        tmpdir.join("dir_rec").join("myb.libspec").write("foo")

        def check1():
            found_my_a = False
            found_my_b = False
            for filepath in found:
                if not filepath.endswith(".libspec"):
                    raise AssertionError("Expected only libspec files to be tracked.")
                if filepath.endswith("my.libspec"):
                    raise AssertionError("Wrong folder tracked.")
                found_my_a = found_my_a or "mya.libspec" in filepath
                found_my_b = found_my_b or "myb.libspec" in filepath

            return found_my_a and found_my_b

        wait_for_test_condition(
            check1,
            msg=lambda: "Expected to find mya.libspec and myb.libspec. Found:\n%s"
            % ("\n".join(found),),
        )

        # not listened
        tmpdir.join("dir_not_rec").join("another").mkdir()
        tmpdir.join("dir_not_rec").join("another").join("myc.txt").write("foo")
        tmpdir.join("dir_not_rec").join("another").join("myc.libspec").write("foo")

        # listened
        tmpdir.join("dir_rec").join("another").mkdir()
        tmpdir.join("dir_rec").join("another").join("myd.txt").write("foo")
        tmpdir.join("dir_rec").join("another").join("myd.libspec").write("foo")

        del found[:]

        def check2():
            found_my_d = False
            for filepath in found:
                if not filepath.endswith(".libspec"):
                    raise AssertionError("Expected only libspec files to be tracked.")
                if filepath.endswith("myc.libspec"):
                    raise AssertionError("Wrong folder tracked.")
                found_my_d = found_my_d or "myd.libspec" in filepath

            return found_my_d

        wait_for_test_condition(
            check2,
            msg=lambda: "Expected to find myd.libspec. Found:\n%s"
            % ("\n".join(found),),
        )

        watch.stop_tracking()
        del found[:]
        tmpdir.join("dir_rec").join("mye.txt").write("foo")
        tmpdir.join("dir_rec").join("mye.libspec").write("foo")

        # Give time to check if some change arrives.
        time.sleep(1)
        assert not found

    finally:
        notifier.dispose()
        observer.dispose()


def test_watchdog_only_recursive(tmpdir):
    from robocorp_ls_core import watchdog_wrapper

    watchdog_wrapper._import_watchdog()

    import watchdog
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import os.path

    class Handler(FileSystemEventHandler):
        def __init__(self):
            FileSystemEventHandler.__init__(self)
            self.changes = []

        def on_any_event(self, event):
            print(event.src_path)
            self.changes.append(os.path.basename(event.src_path))

    handler = Handler()
    observer = Observer()

    watches = []
    watches.append(observer.schedule(handler, str(tmpdir), recursive=True))

    try:
        observer.start()
        time.sleep(0.1)

        tmpdir.join("my0.txt").write("foo")
        tmpdir.join("dir_rec").mkdir()
        tmpdir.join("dir_rec").join("my1.txt").write("foo")

        expected = {"dir_rec", "my0.txt", "my1.txt"}
        timeout_at = time.time() + 5
        while not expected.issubset(handler.changes) and time.time() < timeout_at:
            time.sleep(0.2)

        if not expected.issubset(handler.changes):
            raise AssertionError(
                f"Did not find expected changes. Found: {handler.changes}"
            )

    finally:
        for watch in watches:
            observer.unschedule(watch)
        observer.stop()
