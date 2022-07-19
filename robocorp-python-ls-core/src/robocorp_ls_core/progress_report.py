import threading

from robocorp_ls_core.protocols import IEndPoint, IDirCache, IProgressReporter
from contextlib import contextmanager
from typing import Optional, Iterator, Dict
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import implements
import os


log = get_logger(__name__)


def _next_id():
    # Note: changed to uuid from incremental because multiple processes
    # may start the progress and it shouldn't conflict from one to the
    # other.
    import uuid

    return str(uuid.uuid4()) + "-" + str(os.getpid())


_progress_id_to_progress_reporter: Dict[str, "_ProgressReporter"] = {}


class _ProgressReporter(object):

    _MIN_TIME = 0.25

    def __init__(
        self,
        endpoint: IEndPoint,
        title: str,
        dir_cache: Optional[IDirCache],
        elapsed_time_key=None,
        cancellable: bool = False,
    ) -> None:
        from robocorp_ls_core.timeouts import TimeoutTracker
        import time

        self.endpoint = endpoint
        self.title = title

        self._started = False
        self._finished = False

        self._lock = threading.Lock()
        self._id = _next_id()

        self._expected_time = None
        self._initial_time = time.time()

        self._additional_info: str = ""
        self._cancellable = cancellable
        self._cancelled = False

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

    @property
    def id(self):
        return self._id

    def cancel(self):
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def _on_first_timeout(self):
        with self._lock:
            if not self._finished and not self._started:
                self._started = True
                self.endpoint.notify(
                    "$/customProgress",
                    {
                        "kind": "begin",
                        "id": self._id,
                        "title": self.title,
                        "cancellable": self._cancellable,
                    },
                )
                if self._expected_time:
                    update_time = self._expected_time / 30.0
                else:
                    update_time = 0.25

                self.timeout_tracker.call_on_timeout(
                    update_time, self._on_recurrent_timeout
                )

    def _on_recurrent_timeout(self) -> None:
        import time

        with self._lock:
            if not self._finished and self._started:
                elapsed_time = time.time() - self._initial_time
                expected_time = self._expected_time

                if not self._additional_info:
                    msg = "Elapsed: %.1fs" % (elapsed_time,)
                else:
                    msg = "Elapsed: %.1fs : %s" % (
                        elapsed_time,
                        self._additional_info,
                    )

                args = {
                    "kind": "report",
                    "id": self._id,
                    "message": msg,
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

    @implements(IProgressReporter.set_additional_info)
    def set_additional_info(self, additional_info: str) -> None:
        self._additional_info = additional_info

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

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IProgressReporter = check_implements(self)


_progress_context = threading.local()


def get_current_progress_reporter() -> Optional[_ProgressReporter]:
    try:
        try:
            stack = _progress_context._stack
        except AttributeError:
            return None
        else:
            try:
                return stack[-1]
            except IndexError:
                return None
    except Exception:
        log.exception("Unexpected error getting current progress reporter.")
        return None


class ProgressWrapperForTotalWork:
    """
    Wraps an IProgressReporter to have a quick way to show stes/total steps.

    i.e.:

    with progress_context(...) as progress_reporter:
        progress_wrapper = ProgressWrapperForTotalWork(progress_reporter)

        # Schedule many steps and at each point call.
        progress_reporter.increment_total_steps()

        # When a step is done, increment steps done.
        progress_reporter.increment_step_done()
    """

    def __init__(
        self,
        progress_reporter: IProgressReporter,
        message: str = "%s of %s",
    ) -> None:
        self.progress_reporter = progress_reporter
        self.message = message
        self._lock = threading.Lock()
        self._total_steps = 0
        self._current_step = 0

    def increment_total_steps(self):
        with self._lock:
            self._total_steps += 1
            self._update_message()

    def increment_step_done(self):
        with self._lock:
            self._current_step += 1
            self._update_message()

    def _update_message(self):
        self.progress_reporter.set_additional_info(
            self.message % (self._current_step, self._total_steps)
        )


def cancel(progress_id: str) -> bool:
    progress_reporter = _progress_id_to_progress_reporter.get(progress_id)
    if progress_reporter:
        progress_reporter.cancel()
        return True
    return False


@contextmanager
def progress_context(
    endpoint: IEndPoint,
    title: str,
    dir_cache: Optional[IDirCache],
    elapsed_time_key=None,
    cancellable: bool = False,
) -> Iterator[IProgressReporter]:
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
        endpoint,
        title,
        dir_cache,
        elapsed_time_key=elapsed_time_key,
        cancellable=cancellable,
    )
    _progress_id_to_progress_reporter[progress_reporter.id] = progress_reporter
    try:
        stack = _progress_context._stack
    except AttributeError:
        stack = _progress_context._stack = []

    stack.append(progress_reporter)
    try:
        yield progress_reporter
    finally:
        del _progress_id_to_progress_reporter[progress_reporter.id]
        del stack[-1]
        progress_reporter.finish()
