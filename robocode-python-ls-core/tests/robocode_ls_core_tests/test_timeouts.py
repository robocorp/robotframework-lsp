import pytest
import time
from robocode_ls_core import timeouts
from robocode_ls_core.basic import wait_for_condition


@pytest.yield_fixture(autouse=True)
def _enable_debug_msgs():
    original = timeouts._DEBUG
    timeouts._DEBUG = True
    yield
    timeouts._DEBUG = original


def test_timeout():

    called = []

    def on_timeout(arg):
        assert arg == 1
        called.append(time.time())

    timeout_tracker = timeouts.TimeoutTracker()
    curtime = time.time()
    timeout = 0.2
    timeout_tracker.call_on_timeout(timeout, on_timeout, kwargs={"arg": 1})
    wait_for_condition(lambda: len(called) > 0)

    assert called
    assert called[0] >= curtime + timeout

    del called[:]
    with timeout_tracker.call_on_timeout(1.5, on_timeout, kwargs={"arg": 2}):
        time.sleep(0.5)

    assert not called
    time.sleep(2)
    assert not called
