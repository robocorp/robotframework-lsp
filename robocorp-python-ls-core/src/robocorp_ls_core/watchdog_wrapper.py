"""
Helper to wrap watchdog.
"""
import warnings
import os.path
import sys
import logging
import threading
import weakref
from typing import List, Tuple, Optional, Set, Sequence, Any
from robocorp_ls_core.uris import normalize_drive

log = logging.getLogger(__name__)

__file__ = os.path.abspath(__file__)  # @ReservedAssignment

# Hack so that we don't break the runtime on versions prior to Python 3.8.
if sys.version_info[:2] < (3, 8):

    class Protocol(object):
        pass


else:
    from typing import Protocol


class PathInfo(object):
    __slots__ = ["path", "recursive"]

    def __init__(self, path: str, recursive: bool):
        path = str(path)
        self.path = normalize_drive(path)
        self.recursive = recursive

    def __eq__(self, o):
        if isinstance(o, PathInfo):
            return o.path == self.path and o.recursive == self.recursive

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self, *args, **kwargs):
        return hash(tuple(self.path, self.recursive))

    def __str__(self):
        return f"PathInfo[{self.path}, {self.recursive}]"

    __repr__ = __str__


class IFSCallback(Protocol):
    def __call__(self, src_path, *call_args):
        pass


class IFSWatch(Protocol):
    def stop_tracking(self):
        pass


class IFSObserver(Protocol):
    def notify_on_any_change(
        self,
        paths: List[PathInfo],
        on_change: IFSCallback,
        call_args=(),
        extensions: Optional[Sequence[str]] = None,
    ) -> IFSWatch:
        pass

    def dispose(self):
        pass


def _get_watchdog_lib_dir():
    parent_dir = os.path.dirname(__file__)
    watchdog_dir = os.path.join(parent_dir, "libs", "watchdog_lib")
    if not os.path.exists(watchdog_dir):
        raise RuntimeError("Expected: %s to exist." % (watchdog_dir,))

    internal = os.path.join(watchdog_dir, "watchdog")
    if not os.path.exists(internal):
        raise RuntimeError(
            "Expected: %s to exist (contents: %s)."
            % (internal, os.listdir(watchdog_dir))
        )

    watchdog_init = os.path.join(internal, "__init__.py")
    if not os.path.exists(watchdog_init):
        raise RuntimeError(
            "Expected: %s to exist (contents: %s)."
            % (watchdog_init, os.listdir(internal))
        )

    return watchdog_dir


def _import_watchdog():
    warnings.filterwarnings("ignore", message=".*failed to import fsevents.*")

    try:
        import watchdog
    except ImportError:
        sys.path.append(_get_watchdog_lib_dir())
        import watchdog  # @UnusedImport


def _get_fsnotify_lib_dir():
    parent_dir = os.path.dirname(__file__)
    fsnotify_dir = os.path.join(parent_dir, "libs", "fsnotify_lib")
    if not os.path.exists(fsnotify_dir):
        msg = "Expected: %s to exist.\nDetails:\n" % (fsnotify_dir,)
        check = fsnotify_dir
        while True:
            dirname = os.path.dirname(check)
            exists = os.path.exists(dirname)
            msg += f"{dirname} exists: {exists}\n"
            if exists:
                msg += f"{dirname} contents: {os.listdir(dirname)}\n"

            if not dirname or dirname == check or exists:
                break
            check = dirname

        raise RuntimeError(msg)
    return fsnotify_dir


def _import_fsnotify():
    try:
        import fsnotify
    except ImportError:
        sys.path.append(_get_fsnotify_lib_dir())
        import fsnotify  # @UnusedImport


class _Notifier(threading.Thread):
    def __init__(
        self, callback, timeout: int, extensions: Optional[Tuple[str, ...]] = None
    ):
        """
        :param callback:
            Callable which should be called when a file with the given extension changes.
        :param timeout:
            The amount of time which should elapse to send notifications (so, multiple
            modifications of the same file will be sent as a single notification).
        :param extensions:
            Only notify file changes of the given extensions.
        """
        threading.Thread.__init__(self)
        self.name = "FS Notifier Thread (_Notifier class)"
        self.daemon = True

        self._changes: Set[tuple] = set()
        self._event = threading.Event()
        self._timeout = timeout
        self._disposed = False
        self._callback = callback
        self._extensions = extensions

    def run(self):
        import time

        while not self._disposed:
            self._event.wait()
            time.sleep(self._timeout)
            if self._disposed:
                return

            changes = self._changes
            self._changes = set()
            for src_path_and_call_args in changes:
                try:
                    self._callback(*src_path_and_call_args)
                except:
                    log.exception(
                        "Error handling change on: %s", src_path_and_call_args
                    )
            self._event.clear()

    def on_change(self, src_path, *call_args):
        if self._extensions:
            for ext in self._extensions:
                if src_path.lower().endswith(ext):
                    # Ok, proceed to notify.
                    break
            else:
                # Skip this notification as it's not in one of the available
                # extensions.
                return
        src_path = normalize_drive(src_path)
        self._changes.add((src_path,) + tuple(call_args))
        self._event.set()

    def dispose(self):
        self._disposed = True
        self._event.set()


def create_notifier(callback, timeout, extensions=None):
    notifier = _Notifier(callback, timeout, extensions)
    notifier.start()
    return notifier


class _DummyWatchList(object):
    def stop_tracking(self):
        pass

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSWatch = check_implements(self)


class _FSNotifyWatchList(object):
    def __init__(self, new_tracked_paths, new_notifications, observer):
        """
        :param List[fsnotify.TrackedPath] new_tracked_paths:

        :param Tuple[str, Callback, Tuple[...], bool] new_notifications:
            (path.path, on_change, call_args, recursive)

        :param _FSNotifyObserver observer:
        """
        import fsnotify

        self._new_tracked_paths: List[fsnotify.TrackedPath] = new_tracked_paths
        self._new_notifications = new_notifications
        self._observer = weakref.ref(observer)

    def stop_tracking(self):
        observer: Optional[_FSNotifyObserver] = self._observer()
        if observer is not None and self._new_tracked_paths:
            observer._stop_tracking(self._new_tracked_paths, self._new_notifications)
        self._new_tracked_paths = []
        self._new_notifications = []

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSWatch = check_implements(self)


class _FSNotifyObserver(threading.Thread):
    def __init__(self, extensions: Optional[Tuple[str, ...]]):
        from robocorp_ls_core import load_ignored_dirs

        threading.Thread.__init__(self)
        import fsnotify

        self.name = "_FSNotifyObserver"
        self.daemon = True

        self._disposed = threading.Event()

        if extensions is None:
            extensions = ()
        else:
            extensions = tuple(extensions)

        watcher = self._watcher = fsnotify.Watcher()
        poll_time_str: Optional[str] = os.environ.get("ROBOTFRAMEWORK_LS_POLL_TIME")
        watcher.target_time_for_notification = 4.0
        watcher.target_time_for_single_scan = 4.0

        if poll_time_str:
            try:
                poll_time = int(poll_time_str)
            except Exception:
                log.exception(
                    "Unable to convert ROBOTFRAMEWORK_LS_POLL_TIME (%s) to an int.",
                    poll_time,
                )
            else:
                watcher.target_time_for_notification = poll_time
                watcher.target_time_for_single_scan = poll_time

        watcher.accepted_file_extensions = extensions
        watcher.accept_directory = load_ignored_dirs.create_accept_directory_callable()

        self._all_paths_to_track: List[fsnotify.TrackedPath] = []
        self._lock = threading.Lock()
        self._notifications: List[Tuple[str, Any, List[Any], bool]] = []
        self._was_started = False

    def dispose(self):
        if not self._disposed.is_set():
            self._disposed.set()
            self._watcher.dispose()

    _dir_separators: Tuple[str, ...] = ("/",)
    if sys.platform == "win32":
        _dir_separators = ("\\", "/")

    def run(self):
        log.debug("Started listening on _FSNotifyObserver.")
        try:
            while not self._disposed.is_set():
                dir_separators = self._dir_separators
                for _change, src_path in self._watcher.iter_changes():
                    src_path_lower = src_path.lower()
                    for path, on_change, call_args, recursive in self._notifications:
                        path_lower = path.lower()
                        if src_path_lower.startswith(path_lower):
                            if len(src_path_lower) == len(path_lower):
                                pass
                            elif src_path_lower[len(path_lower)] in dir_separators:
                                pass
                            else:
                                continue

                            if recursive:
                                on_change(normalize_drive(src_path), *call_args)
                            else:
                                remainder = src_path_lower[len(path_lower) + 1 :]
                                count_dir_sep = 0
                                for dir_sep in dir_separators:
                                    count_dir_sep += remainder.count(dir_sep)
                                if count_dir_sep == 0:
                                    on_change(normalize_drive(src_path), *call_args)

        except:
            log.exception("Error collecting changes in _FSNotifyObserver.")
        finally:
            log.debug("Finished listening on _FSNotifyObserver.")

    def _tracked_paths_set_on_thread(self):
        with self._lock:
            all_paths_to_track = self._all_paths_to_track[:]
        self._watcher.set_tracked_paths(all_paths_to_track)

    def _stop_tracking(self, new_paths_to_track, new_notifications):
        with self._lock:
            for path in new_paths_to_track:
                self._all_paths_to_track.remove(path)
            for notification in new_notifications:
                self._notifications.remove(notification)
        threading.Thread(target=self._tracked_paths_set_on_thread).start()

    def notify_on_any_change(
        self,
        paths: List[PathInfo],
        on_change: IFSCallback,
        call_args=(),
        extensions: Optional[Sequence[str]] = None,
    ) -> IFSWatch:
        if self._disposed.is_set():
            return _DummyWatchList()

        import fsnotify

        used_on_change = on_change
        if extensions:

            def on_change_with_extensions(src_path, *args):
                lower = src_path.lower()
                if lower.endswith(extensions):
                    on_change(src_path, *args)

            used_on_change = on_change_with_extensions

        with self._lock:
            new_paths_to_track = []
            new_notifications = []
            for path in paths:
                tracked_path = fsnotify.TrackedPath(path.path, path.recursive)
                new_paths_to_track.append(tracked_path)
                new_notifications.append(
                    (path.path, used_on_change, call_args, path.recursive)
                )

            self._notifications.extend(new_notifications)
            self._all_paths_to_track.extend(new_paths_to_track)

        threading.Thread(target=self._tracked_paths_set_on_thread).start()
        if not self._was_started:
            with self._lock:
                # Check again with the lock in place.
                if not self._was_started:
                    self._was_started = True
                    self.start()

        return _FSNotifyWatchList(new_paths_to_track, new_notifications, self)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSObserver = check_implements(self)


class _WatchdogWatchList(object):
    def __init__(self, watches, observer, info_to_count):
        self.watches = watches
        self._info_to_count = info_to_count
        self._observer = weakref.ref(observer)

    def stop_tracking(self):
        observer = self._observer()
        if observer is not None:
            for watch in self.watches:
                count = self._info_to_count[watch.key]
                if count > 1:
                    self._info_to_count[watch.key] = count - 1
                    continue
                else:
                    del self._info_to_count[watch.key]

                try:
                    observer.unschedule(watch)
                except Exception:
                    pass
        self.watches = []

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSWatch = check_implements(self)


class _WatchdogObserver(object):
    def __init__(self, extensions=None):
        from watchdog.observers import Observer

        self._observer = Observer()
        self._started = False
        self._extensions = extensions
        self._info_to_count = {}

    def dispose(self):
        self._observer.stop()

    def _start(self):
        if not self._started:
            self._started = True
            self._observer.start()

    def notify_on_any_change(
        self,
        paths: List[PathInfo],
        on_change: IFSCallback,
        call_args=(),
        extensions: Optional[Sequence[str]] = None,
    ) -> IFSWatch:
        """
        To be used as:

        notifier = create_notifier(callback=on_file_change, timeout=0.5)

        observer = create_observer()

        watch = observer.notify_on_any_change(
            [PathInfo('a', recursive=True)],
            notifier.on_change,
            extensions=('.py', '.robot'),
        )
        ...
        watch.stop_tracking()

        notifier.dispose()
        observer.dispose()

        Multiple changes on the same file will be sent as a single change (if
        the changes occur during the available timeout).

        :param list(PathInfo) paths:
        :param list(str) extensions:
            The file extensions that should be tracked.
        """
        from watchdog.events import FileSystemEventHandler

        if not extensions:
            extensions = self._extensions

        class _Handler(FileSystemEventHandler):
            def __init__(
                self,
            ):
                FileSystemEventHandler.__init__(self)

            def on_any_event(self, event):
                # with open("c:/temp/out.txt", "a+") as stream:
                #     stream.write(f"Event src: {event.src_path}\n")
                #     try:
                #         stream.write(f"Event dest: {event.dest_path}\n")
                #     except:
                #         pass

                if extensions is not None:
                    for ext in extensions:
                        if event.src_path.endswith(ext):
                            break
                    else:
                        return
                # Note: notify on directory and file changes.
                on_change(event.src_path, *call_args)
                try:
                    dest_path = event.dest_path
                except AttributeError:
                    pass
                else:
                    if dest_path:
                        on_change(dest_path, *call_args)

        handler = _Handler()
        watches = []

        for path_info in paths:
            # with open("c:/temp/out.txt", "a+") as stream:
            #     stream.write(
            #         f"schedule: {path_info.path}, recursive: {path_info.recursive}\n"
            #     )

            watch = self._observer.schedule(
                handler, path_info.path, recursive=path_info.recursive
            )
            key = watch.key
            if key not in self._info_to_count:
                self._info_to_count[key] = 1
            else:
                self._info_to_count[key] = self._info_to_count[key] + 1

            watches.append(watch)

        self._start()
        return _WatchdogWatchList(watches, self._observer, self._info_to_count)

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSObserver = check_implements(self)


class _DummyFSObserver(object):
    def notify_on_any_change(
        self,
        paths: List[PathInfo],
        on_change: IFSCallback,
        call_args=(),
        extensions: Optional[Sequence[str]] = None,
    ) -> IFSWatch:
        return _DummyWatchList()

    def dispose(self):
        pass

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: IFSObserver = check_implements(self)


def create_observer(backend: str, extensions: Optional[Tuple[str, ...]]) -> IFSObserver:
    """
    :param backend:
        The backend to use.
        'fsnotify', 'watchdog' or 'dummy'.
    """
    if backend == "watchdog":
        _import_watchdog()
        return _WatchdogObserver(extensions)

    elif backend == "fsnotify":
        _import_fsnotify()
        return _FSNotifyObserver(extensions)

    elif backend == "dummy":
        return _DummyFSObserver()

    raise AssertionError(f"Unhandled observer: {backend}")


def create_remote_observer(
    backend: str, extensions: Optional[Tuple[str, ...]]
) -> IFSObserver:
    """
    :param backend:
        The backend to use.
        'fsnotify' or 'watchdog'.
    """
    assert backend in ("watchdog", "fsnotify")
    from robocorp_ls_core.remote_fs_observer_impl import RemoteFSObserver

    return RemoteFSObserver(backend, extensions)
