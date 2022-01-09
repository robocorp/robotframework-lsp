from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class Callback(object):
    """
    Note that it's thread safe to register/unregister callbacks while callbacks
    are being notified, but it's not thread-safe to register/unregister at the
    same time in multiple threads.
    """

    def __init__(self):
        self._callbacks = []

    def register(self, callback):
        new_callbacks = self._callbacks[:]
        new_callbacks.append(callback)
        self._callbacks = new_callbacks

    def unregister(self, callback):
        new_callbacks = [x for x in self._callbacks if x != callback]
        self._callbacks = new_callbacks

    def __call__(self, *args, **kwargs):
        for c in self._callbacks:
            try:
                c(*args, **kwargs)
            except:
                log.exception("Error in callback.")


class CallbackWithReturn(Callback):
    """
    A callback that returns the first non-None value returned
    from a registered caller.
    """

    def __call__(self, *args, **kwargs):
        for c in self._callbacks:
            try:
                ret = c(*args, **kwargs)
            except:
                log.exception("Error in callback with return.")
                continue
            if ret is not None:
                return ret
        return None
