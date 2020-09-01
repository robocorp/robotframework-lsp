import threading
import time
import weakref

from robocorp_ls_core.constants import NULL
from robocorp_ls_core.protocols import ITimeoutHandle
from robocorp_ls_core.robotframework_log import get_logger


_DEBUG = False  # Default should be False as this can be very verbose.

log = get_logger(__name__)


class _TimeoutThread(threading.Thread):
    """
    The idea in this class is that it should be usually stopped waiting
    for the next event to be called (paused in a threading.Event.wait).

    When a new handle is added it sets the event so that it processes the handles and
    then keeps on waiting as needed again.

    This is done so that it's a bit more optimized than creating many Timer threads.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self._event = threading.Event()
        self._handles = []
        self.daemon = True

        # We could probably do things valid without this lock so that it's possible to add
        # handles while processing, but the implementation would also be harder to follow,
        # so, for now, we're either processing or adding handles, not both at the same time.
        self._timeout_thread_lock = threading.Lock()
        self._kill_received = False

    def run(self):
        wait_time = None
        while not self._kill_received:
            if _DEBUG:
                if wait_time is None:
                    log.critical("timeouts: Wait until a new handle is added.")
                else:
                    log.critical("timeouts: Next wait time: %s.", wait_time)
            self._event.wait(wait_time)

            if self._kill_received:
                self._handles = []
                return

            wait_time = self.process_handles()

    def do_kill_thread(self):
        with self._timeout_thread_lock:
            self._kill_received = True
            self._event.set()

    def process_handles(self):
        """
        :return int:
            Returns the time we should be waiting for to process the next event properly.
        """
        exec_new_handles = []
        min_handle_timeout = None

        try:
            with self._timeout_thread_lock:
                if _DEBUG:
                    log.critical("timeouts: Processing handles")
                self._event.clear()
                handles = self._handles
                new_handles = self._handles = []

                # Do all the processing based on this time (we want to consider snapshots
                # of processing time -- anything not processed now may be processed at the
                # next snapshot).
                curtime = time.time()

                for handle in handles:
                    if curtime < handle.abs_timeout and not handle.disposed:
                        # It still didn't time out.
                        if _DEBUG:
                            log.critical("timeouts: Handle NOT processed: %s", handle)
                        new_handles.append(handle)
                        if min_handle_timeout is None:
                            min_handle_timeout = handle.abs_timeout

                        elif handle.abs_timeout < min_handle_timeout:
                            min_handle_timeout = handle.abs_timeout

                    else:
                        if _DEBUG:
                            log.critical("timeouts: Handle processed: %s", handle)
                        # Timed out (or disposed), so, let's execute it (should be no-op if disposed).
                        exec_new_handles.append(handle)

        finally:
            # Only call the handles after releasing the lock (so that this
            # execution can add a new handler -- otherwise it'd deadlock).
            for handle in exec_new_handles:
                try:
                    handle.exec_on_timeout()
                except:
                    log.exception()

        if min_handle_timeout is None:
            return None
        else:
            timeout = min_handle_timeout - curtime
            if timeout <= 0:
                log.critical("timeouts: Expected timeout to be > 0. Found: %s", timeout)

            return timeout

    def add_on_timeout_handle(self, handle):
        with self._timeout_thread_lock:
            self._handles.append(handle)
            self._event.set()


class _OnTimeoutHandle(object):
    def __init__(self, tracker, abs_timeout, on_timeout, kwargs):
        self._str = "_OnTimeoutHandle(%s)" % (on_timeout,)

        self._tracker = weakref.ref(tracker)
        self.abs_timeout = abs_timeout
        self.on_timeout = on_timeout
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.disposed = False
        self._lock = threading.Lock()

    def exec_on_timeout(self):
        with self._lock:
            kwargs = self.kwargs
            on_timeout = self.on_timeout
            if self.disposed:
                return

            self.disposed = True
            self.kwargs = None
            self.on_timeout = None
            self._lock = NULL  # We don't need it anymore

        # The actual call doesn't need the lock anymore.
        try:
            if _DEBUG:
                log.critical(
                    "timeouts: Calling on timeout: %s with kwargs: %s",
                    on_timeout,
                    kwargs,
                )

            on_timeout(**kwargs)
        except Exception:
            log.exception("timeouts: Exception on callback timeout.")

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            self.disposed = True
            self.kwargs = None
            self.on_timeout = None
            self._lock = NULL  # We don't need it anymore

    def __str__(self):
        return self._str

    __repr__ = __str__


class TimeoutTracker(object):
    """
    This is a helper class to track the timeout of something.
    """

    _instance_lock = threading.Lock()
    _instance = None

    @classmethod
    def get_singleton(cls) -> "TimeoutTracker":
        instance = cls._instance
        if instance is None:
            with cls._instance_lock:
                instance = cls._instance
                if instance is None:
                    instance = cls._instance = TimeoutTracker()
        return instance

    def __init__(self):
        self._thread = None
        self._tracker_lock = threading.Lock()

    def call_on_timeout(self, timeout, on_timeout, kwargs=None) -> ITimeoutHandle:
        """
        This can be called regularly to always execute the given function after a given timeout:

        call_on_timeout(10, on_timeout)


        Or as a context manager to stop the method from being called if it finishes before the timeout
        elapses:

        with call_on_timeout(10, on_timeout):
            ...

        Note: the callback will be called from a thread.
        """
        with self._tracker_lock:
            if self._thread is None:
                if _DEBUG:
                    log.critical("timeouts: Created _TimeoutThread.")

                thread = self._thread = _TimeoutThread()
                self._thread.start()

                def on_die(*args, **kwargs):
                    # Finish that thread when the TimeoutTracker is collected.
                    thread.do_kill_thread()

                self._ref = weakref.ref(self, on_die)

            curtime = time.time()
            handle = _OnTimeoutHandle(self, curtime + timeout, on_timeout, kwargs)
            if _DEBUG:
                log.critical("timeouts: Added handle: %s.", handle)
            self._thread.add_on_timeout_handle(handle)
            return handle
