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
            "_watchdog_fsevents.cpython-38-darwin.so",
        )
    )
    assert os.path.exists(
        os.path.join(
            watchdog_wrapper._get_watchdog_lib_dir(),
            "_watchdog_fsevents.cpython-39-darwin.so",
        )
    )
    assert os.path.exists(
        os.path.join(
            watchdog_wrapper._get_watchdog_lib_dir(),
            "_watchdog_fsevents.cpython-310-darwin.so",
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


@pytest.mark.parametrize("backend", ["watchdog", "fsnotify"])
def test_watchdog_rename_folder(tmpdir, backend):
    from robocorp_ls_core import watchdog_wrapper
    from robocorp_ls_core.watchdog_wrapper import PathInfo
    from robocorp_ls_core.basic import wait_for_expected_func_return
    import os

    dir_rec = tmpdir.join("dir_rec")
    dir_rec.mkdir()

    found = set()

    def on_change(filepath, *args):
        f = str(filepath)
        n = str(dir_rec)
        rel = os.path.relpath(f, n).replace("\\", "/")
        if rel.endswith(".txt"):
            found.add(rel)

    notifier = watchdog_wrapper.create_notifier(on_change, timeout=0.1)
    observer = watchdog_wrapper.create_observer(backend, None)

    watch = observer.notify_on_any_change(
        [
            PathInfo(dir_rec, True),
        ],
        notifier.on_change,
    )

    try:
        folder = dir_rec.join("folder")
        folder.mkdir()

        time.sleep(1)
        folder.join("my.txt").write_text("something", encoding="utf-8")
        wait_for_expected_func_return(lambda: found, {"folder/my.txt"})
        found.clear()
        folder.rename(dir_rec.join("renamed"))
        wait_for_expected_func_return(
            lambda: found, {"folder/my.txt", "renamed/my.txt"}
        )
        found.clear()
        dir_rec.join("renamed").remove(rec=True)
        wait_for_expected_func_return(lambda: found, {"renamed/my.txt"})
    finally:
        watch.stop_tracking()
        notifier.dispose()
        observer.dispose()


@pytest.mark.parametrize("backend", ["watchdog", "fsnotify"])
def test_watchdog_conflicts(tmpdir, backend):
    from robocorp_ls_core import watchdog_wrapper
    from robocorp_ls_core.watchdog_wrapper import PathInfo
    from robocorp_ls_core.unittest_tools.fixtures import wait_for_test_condition
    import os

    dir_rec = tmpdir.join("dir_rec")
    dir_rec.mkdir()

    found = set()

    def on_change(filepath, *args):
        found.add(os.path.basename(filepath))

    found2 = set()

    def on_change2(filepath, *args):
        found2.add(os.path.basename(filepath))

    observer = watchdog_wrapper.create_observer(backend, None)

    notifier = watchdog_wrapper.create_notifier(on_change, timeout=0.1)
    notifier2 = watchdog_wrapper.create_notifier(on_change2, timeout=0.1)

    watch = observer.notify_on_any_change(
        [
            PathInfo(dir_rec, True),
        ],
        notifier.on_change,
    )
    watch2 = observer.notify_on_any_change(
        [
            PathInfo(dir_rec, False),
        ],
        notifier2.on_change,
    )

    # It can take a bit of time for listeners to be setup
    time.sleep(2)

    try:
        dir_rec.join("mya.txt").write("foo")
        dir_rec.join("inner").mkdir()
        dir_rec.join("inner").join("myb.txt").write("bar")

        def collect_basenames():
            return found

        def check1():
            expected = {"mya.txt", "myb.txt"}
            return collect_basenames().issuperset(expected)

        wait_for_test_condition(
            check1,
            msg=lambda: f"Basenames found: {collect_basenames()}",
        )

        def check2():
            return found2.issuperset({"mya.txt"}) and "myb.txt" not in found2

        wait_for_test_condition(
            check2,
            msg=lambda: f"Basenames found: {found2}",
        )
    finally:
        watch.stop_tracking()
        watch2.stop_tracking()
        notifier.dispose()
        notifier2.dispose()
        observer.dispose()


@pytest.mark.parametrize("backend", ["watchdog", "fsnotify"])
def test_watchdog_all(tmpdir, backend):
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
    observer = watchdog_wrapper.create_observer(backend, None)

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


@pytest.mark.parametrize("backend", ["watchdog", "fsnotify"])
def test_watchdog_extensions(tmpdir, backend):
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
    observer = watchdog_wrapper.create_observer(backend, (".libspec",))

    watch = observer.notify_on_any_change(
        [
            PathInfo(tmpdir.join("dir_not_rec"), False),
            PathInfo(tmpdir.join("dir_rec"), True),
        ],
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
