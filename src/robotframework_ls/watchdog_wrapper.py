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
        self.path = str(path)
        self.recursive = recursive


def _import_watchdog():
    warnings.filterwarnings("ignore", message=".*failed to import fsevents.*")

    try:
        import watchdog
    except ImportError:
        _parent_dir = os.path.dirname(__file__)
        _watchdog_dir = os.path.join(_parent_dir, "libs", "watchdog_lib")
        if not os.path.exists(_watchdog_dir):
            raise RuntimeError("Expected: %s to exist." % (_watchdog_dir,))
        sys.path.append(_watchdog_dir)
        import watchdog  # @UnusedImport


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
        self.name = "Watchdog _Notifier"
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


class _WatchList(object):
    def __init__(self, watches, observer):
        self.watches = watches
        self._observer = weakref.ref(observer)

    def stop_tracking(self):
        observer = self._observer()
        if observer is not None:
            for watch in self.watches:
                observer.unschedule(watch)
        self.watches = []


class _Observer(object):
    def __init__(self):
        _import_watchdog()
        from watchdog.observers import Observer

        self._observer = Observer()
        self._started = False

    def dispose(self):
        self._observer.stop()

    def _start(self):
        if not self._started:
            self._started = True
            self._observer.start()

    def notify_on_extensions_change(self, paths, extensions, on_change, call_args=()):
        """
        To be used as:
        
        notifier = create_notifier(callback=on_file_change, timeout=0.5)
        
        observer = create_observer() 
        
        watch = observer.notify_on_extensions_change(
            [PathInfo('a', recursive=True)],
            ['libspec'], 
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
        _import_watchdog()

        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler):
            def __init__(self, extensions):
                FileSystemEventHandler.__init__(self)
                extensions = [ext.lower() for ext in extensions]
                self._extensions = extensions

            def on_any_event(self, event):
                if event.is_directory:
                    return None
                for ext in self._extensions:
                    if event.src_path.lower().endswith(ext):
                        on_change(event.src_path, *call_args)

        handler = _Handler(extensions)
        watches = []
        for path_info in paths:
            watches.append(
                self._observer.schedule(
                    handler, path_info.path, recursive=path_info.recursive
                )
            )

        self._start()
        return _WatchList(watches, self._observer)


def create_observer():
    return _Observer()
