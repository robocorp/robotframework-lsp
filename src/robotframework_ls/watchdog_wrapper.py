import warnings
import os.path
import sys
import logging

log = logging.getLogger(__name__)

__file__ = os.path.abspath(__file__)


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


def notify_on_extensions_change(paths, extensions, callback, timeout=0.3):
    """
    To be used as:
    
    handle = notify_on_extensions_change(
        [PathInfo('a', recursive=True)],
        ['libspec'], 
        on_change,
        timeout=0.5,
    )
    ...
    handle.stop()
    
    Multiple changes on the same file will be sent as a single change (if
    the changes occur during the available timeout).
    
    :param list(PathInfo) paths:
    :param list(str) extensions:
        The file extensions that should be tracked.
    :param callback:
        Callable which should be called when a file with the given extension changes.
    :param timeout:
        The amount of time which should elapse to send notifications (so, multiple
        modifications of the same file will be sent as a single notification).
    """
    _import_watchdog()

    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import threading

    observer = Observer()

    class _Notifier(threading.Thread):
        def __init__(self, timeout):
            threading.Thread.__init__(self)
            self.name = "Watchdog Notifier"
            self.daemon = True

            self._changes = set()
            self._event = threading.Event()
            self._timeout = timeout

        def run(self):
            import time

            while True:
                self._event.wait()
                time.sleep(self._timeout)
                changes = self._changes
                self._changes = set()
                for src_path in changes:
                    try:
                        callback(src_path)
                    except:
                        log.exception("Error handling change on: %s", src_path)
                self._event.clear()

        def on_change(self, src_path):
            self._changes.add(src_path)
            self._event.set()

    notifier = _Notifier(timeout)

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
                    notifier.on_change(event.src_path)

    handler = _Handler(extensions)
    for path_info in paths:
        observer.schedule(handler, path_info.path, recursive=path_info.recursive)
    observer.start()
    notifier.start()
    return observer
