from functools import partial
import itertools
import threading

from robocorp_ls_core.protocols import IEndPoint, IDirCache
from contextlib import contextmanager
from typing import Optional


next_id = partial(next, itertools.count(1))


class _ProgressReporter(object):

    _MIN_TIME = 0.25

    def __init__(
        self,
        endpoint: IEndPoint,
        title: str,
        dir_cache: Optional[IDirCache],
        elapsed_time_key=None,
    ) -> None:
        from robocorp_ls_core.timeouts import TimeoutTracker
        import time

        self.endpoint = endpoint
        self.title = title

        self._started = False
        self._finished = False

        self._lock = threading.Lock()
        self._id = next_id()

        self._expected_time = None
        self._initial_time = time.time()

        self._dir_cache = dir_cache
        self._last_elapsed_time_key = (
            elapsed_time_key
            if elapsed_time_key is not None
            else ("operation_time", title)
        )
        try:
            if dir_cache:
                expected_time = dir_cache.load(self._last_elapsed_time_key, float)
                # Leave some gap on the expected.
                self._expected_time = expected_time * 1.2
        except KeyError:
            pass

        self._last_progress = 0.0
        self.timeout_tracker = TimeoutTracker.get_singleton()
        self.timeout_tracker.call_on_timeout(self._MIN_TIME, self._on_first_timeout)

    def _on_first_timeout(self):
        with self._lock:
            if not self._finished and not self._started:
                self._started = True
                self.endpoint.notify(
                    "$/customProgress",
                    {"kind": "begin", "id": self._id, "title": self.title},
                )
                if self._expected_time:
                    update_time = self._expected_time / 30.0
                else:
                    update_time = 0.25

                self.timeout_tracker.call_on_timeout(
                    update_time, self._on_recurrent_timeout
                )

    def _on_recurrent_timeout(self):
        import time

        with self._lock:
            if not self._finished and self._started:
                elapsed_time = time.time() - self._initial_time
                expected_time = self._expected_time

                args = {
                    "kind": "report",
                    "id": self._id,
                    "message": "Elapsed: %.1fs" % (elapsed_time,),
                }
                if expected_time:
                    progress = elapsed_time / expected_time
                    if progress > 0.95:
                        progress = 0.95
                    increment = (progress - self._last_progress) * 100
                    self._last_progress = progress
                    args["increment"] = increment

                self.endpoint.notify("$/customProgress", args)
                self.timeout_tracker.call_on_timeout(0.5, self._on_recurrent_timeout)

    def finish(self) -> None:
        import time

        with self._lock:
            if not self._finished:
                self._finished = True
                self.endpoint.notify(
                    "$/customProgress", {"kind": "end", "id": self._id}
                )
                total_elapsed_time = time.time() - self._initial_time
                if total_elapsed_time > self._MIN_TIME:
                    dir_cache = self._dir_cache
                    if dir_cache:
                        dir_cache.store(self._last_elapsed_time_key, total_elapsed_time)


@contextmanager
def progress_context(
    endpoint: IEndPoint,
    title: str,
    dir_cache: Optional[IDirCache],
    elapsed_time_key=None,
):
    """
    Creates a progress context which submits $/customProgress notifications to the
    client.
    
    Automatically updates the progress based on a previous invocation for some
    action with the same title (stores the elapsed time at the dir_cache).
    
    :param dir_cache:
        If None, an estimate for the task is not loaded/saved.
        
    :param elapsed_time_key:
        If None, the default is using the title as an entry in the dir cache,
        otherwise, the given key is used to load/save the time taken in the
        cache dir.
    """
    progress_reporter = _ProgressReporter(
        endpoint, title, dir_cache, elapsed_time_key=elapsed_time_key
    )
    try:
        yield
    finally:
        progress_reporter.finish()
