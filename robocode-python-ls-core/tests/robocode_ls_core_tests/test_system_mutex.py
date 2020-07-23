def test_system_mutex():
    from robocode_ls_core.system_mutex import SystemMutex
    from robocode_ls_core.system_mutex import timed_acquire_mutex
    from robocode_ls_core.subprocess_wrapper import subprocess
    import sys
    import pytest
    import time
    import threading
    import weakref

    mutex_name = "mutex_name_test_system_mutex"

    system_mutex = SystemMutex(mutex_name)
    assert system_mutex.get_mutex_aquired()

    class Check2Thread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.worked = False

        def run(self):
            mutex2 = SystemMutex(mutex_name)
            assert not mutex2.get_mutex_aquired()
            self.worked = True

    t = Check2Thread()
    t.start()
    t.join()
    assert t.worked

    assert not system_mutex.disposed
    system_mutex.release_mutex()
    assert system_mutex.disposed

    mutex3 = SystemMutex(mutex_name)
    assert not mutex3.disposed
    assert mutex3.get_mutex_aquired()
    mutex3 = weakref.ref(mutex3)  # Garbage-collected

    # Calling release more times should not be an error
    system_mutex.release_mutex()

    mutex4 = SystemMutex(mutex_name)
    assert mutex4.get_mutex_aquired()

    with pytest.raises(AssertionError):
        SystemMutex("mutex/")  # Invalid name

    time_to_release_mutex = 1

    def release_mutex():
        time.sleep(time_to_release_mutex)
        mutex4.release_mutex()

    t = threading.Thread(target=release_mutex)
    t.start()

    initial_time = time.time()
    with timed_acquire_mutex(
        mutex_name, check_reentrant=False
    ):  # The current mutex will be released in a thread, so, check_reentrant=False.
        acquired_time = time.time()

        # Should timeout as the lock is already acquired.
        with pytest.raises(RuntimeError) as exc:
            with timed_acquire_mutex(mutex_name, timeout=1):
                pass
        assert "not a reentrant mutex" in str(exc)

        # Must also fail from another process.
        code = """
from robocode_ls_core.system_mutex import timed_acquire_mutex
mutex_name = "mutex_name_test_system_mutex"
with timed_acquire_mutex(mutex_name, timeout=1):
    pass
"""
        with pytest.raises(subprocess.CalledProcessError):
            subprocess.check_call([sys.executable, "-c", code], stderr=subprocess.PIPE)

    assert acquired_time - initial_time > time_to_release_mutex


def test_gen_mutex_name_from_path():
    from robocode_ls_core.system_mutex import generate_mutex_name

    mutex_name = "my/snth\\nsth"
    mutex_name = generate_mutex_name(mutex_name, prefix="my_")
    assert mutex_name == "my_f9c932bf450ef164"
