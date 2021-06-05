class Callback(object):
    def __init__(self):
        self._callbacks = []

    def register(self, callback):
        self._callbacks.append(callback)

    def unregister(self, callback):
        self._callbacks.remove(callback)

    def __call__(self, *args, **kwargs):
        for c in self._callbacks:
            c(*args, **kwargs)
