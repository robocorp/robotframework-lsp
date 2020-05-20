import time


def test_watchdog(tmpdir):
    from robocode_ls_core import watchdog_wrapper
    from robocode_ls_core.watchdog_wrapper import PathInfo
    from robocode_ls_core.unittest_tools.fixtures import wait_for_test_condition

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
