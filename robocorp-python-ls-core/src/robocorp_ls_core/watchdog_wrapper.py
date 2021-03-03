"""
Helper to wrap watchdog.
"""
import warnings
import os.path
import sys
import logging
import threading
import weakref

log = logging.getLogger(__name__)

__file__ = os.path.abspath(__file__)  # @ReservedAssignment


class PathInfo(object):
    __slots__ = ["path", "recursive"]

    def __init__(self, path, recursive):
        path = str(path)
        self.path = path
        self.recursive = recursive

    def __eq__(self, o):
        if isinstance(o, PathInfo):
            return o.path == self.path and o.recursive == self.recursive

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self, *args, **kwargs):
        return hash(tuple(self.path, self.recursive))


def _get_watchdog_lib_dir():
    parent_dir = os.path.dirname(__file__)
    watchdog_dir = os.path.join(parent_dir, "libs", "watchdog_lib")
    if not os.path.exists(watchdog_dir):
        raise RuntimeError("Expected: %s to exist." % (watchdog_dir,))
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
    def __init__(self, callback, timeout):
        """
        :param callback:
            Callable which should be called when a file with the given extension changes.
        :param timeout:
            The amount of time which should elapse to send notifications (so, multiple
            modifications of the same file will be sent as a single notification).
        """
        threading.Thread.__init__(self)
        self.name = "FS Notifier Thread (_Notifier class)"
        self.daemon = True

        self._changes = set()
        self._event = threading.Event()
        self._timeout = timeout
        self._disposed = False
        self._callback = callback

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
        self._changes.add((src_path,) + tuple(call_args))
        self._event.set()

    def dispose(self):
        self._disposed = True
        self._event.set()


def create_notifier(callback, timeout):
    notifier = _Notifier(callback, timeout)
    notifier.start()
    return notifier


class _FSNotifyWatchList(object):
    def __init__(self, new_tracked_paths, new_notifications, observer):
        self._new_tracked_paths = new_tracked_paths
        self._new_notifications = new_notifications
        self._observer = weakref.ref(observer)

    def stop_tracking(self):
        observer = self._observer()
        if observer is not None and self._new_tracked_paths:
            observer._stop_tracking(self._new_tracked_paths, self._new_notifications)
        self._new_tracked_paths = []
        self._new_notifications = []


class _FSNotifyObserver(threading.Thread):
    def __init__(self, extensions):
        threading.Thread.__init__(self)
        import fsnotify

        self.name = "_FSNotifyObserver"
        self.daemon = True

        self._disposed = threading.Event()

        if extensions is None:
            extensions = ()

        watcher = self._watcher = fsnotify.Watcher()
        watcher.target_time_for_notification = 3.0
        watcher.target_time_for_single_scan = 3.0
        watcher.accepted_file_extensions = extensions
        # Could be customizable...
        watcher.ignored_dirs = {
            ".git",
            "__pycache__",
            ".idea",
            "node_modules",
            ".metadata",
        }

        self._all_paths_to_track = []
        self._lock = threading.Lock()
        self._notifications = []

    def dispose(self):
        if not self._disposed.is_set():
            self._disposed.set()
            self._watcher.dispose()

    def run(self):
        while not self._disposed.is_set():
            for _change, src_path in self._watcher.iter_changes():
                lower = src_path.lower()
                for path, on_change, call_args in self._notifications:
                    if lower.startswith(path):
                        on_change(src_path, *call_args)

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

    def notify_on_any_change(self, paths, on_change, call_args=()):
        if self._disposed.is_set():
            return

        import fsnotify

        with self._lock:
            new_paths_to_track = []
            new_notifications = []
            for path in paths:
                tracked_path = fsnotify.TrackedPath(path.path, path.recursive)
                new_paths_to_track.append(tracked_path)
                new_notifications.append((path.path.lower(), on_change, call_args))

            self._notifications.extend(new_notifications)
            self._all_paths_to_track.extend(new_paths_to_track)

        threading.Thread(target=self._tracked_paths_set_on_thread).start()
        if not self.is_alive():
            self.start()

        return _FSNotifyWatchList(new_paths_to_track, new_notifications, self)


class _WatchdogWatchList(object):
    def __init__(self, watches, observer):
        self.watches = watches
        self._observer = weakref.ref(observer)

    def stop_tracking(self):
        observer = self._observer()
        if observer is not None:
            for watch in self.watches:
                observer.unschedule(watch)
        self.watches = []


class _WatchdogObserver(object):
    def __init__(self, extensions=None):
        from watchdog.observers import Observer

        self._observer = Observer()
        self._started = False
        self._extensions = extensions

    def dispose(self):
        self._observer.stop()

    def _start(self):
        if not self._started:
            self._started = True
            self._observer.start()

    def notify_on_any_change(self, paths, on_change, call_args=()):
        """
        To be used as:
        
        notifier = create_notifier(callback=on_file_change, timeout=0.5)
        
        observer = create_observer() 
        
        watch = observer.notify_on_any_change(
            [PathInfo('a', recursive=True)],
            notifier.on_change
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

        extensions = self._extensions

        class _Handler(FileSystemEventHandler):
            def __init__(self,):
                FileSystemEventHandler.__init__(self)

            def on_any_event(self, event):
                if extensions is not None:
                    for ext in extensions:
                        if event.src_path.endswith(ext):
                            break
                    else:
                        return
                # Note: notify on directory and file changes.
                on_change(event.src_path, *call_args)

        handler = _Handler()
        watches = []
        for path_info in paths:
            watches.append(
                self._observer.schedule(
                    handler, path_info.path, recursive=path_info.recursive
                )
            )

        self._start()
        return _WatchdogWatchList(watches, self._observer)


def create_observer(backend, extensions):
    """
    :param backend:
        The backend to use.
        'fsnotify' or 'watchdog'.
    """
    if backend == "watchdog":
        _import_watchdog()
        return _WatchdogObserver(extensions)

    elif backend == "fsnotify":
        _import_fsnotify()
        return _FSNotifyObserver(extensions)

    raise AssertionError(f"Unhandled observer: {backend}")
