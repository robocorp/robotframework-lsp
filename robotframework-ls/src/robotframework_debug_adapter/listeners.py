class _Callback(object):
    def __init__(self):
        self._callbacks = []

    def register(self, callback):
        self._callbacks.append(callback)

    def __call__(self, *args, **kwargs):
        for c in self._callbacks:
            c(*args, **kwargs)


class DebugListener(object):
    ROBOT_LISTENER_API_VERSION = 3

    on_start_suite = _Callback()
    on_end_suite = _Callback()
    on_start_test = _Callback()
    on_end_test = _Callback()

    def start_suite(self, data, result):
        self.on_start_suite(data, result)

    def end_suite(self, data, result):
        self.on_end_suite(data, result)

    def start_test(self, data, result):
        self.on_start_test(data, result)

    def end_test(self, data, result):
        self.on_end_test(data, result)

    # def start_keyword(self, data, result):
    #     # This would be nice, but it's not currently supported.
    #
    # def end_keyword(self, data, result):
    #     # This would be nice, but it's not currently supported.


class DebugListenerV2(object):
    ROBOT_LISTENER_API_VERSION = 2

    on_start_keyword = _Callback()
    on_end_keyword = _Callback()

    def start_suite(self, name, attributes):
        pass

    def end_suite(self, name, attributes):
        pass

    def start_test(self, name, attributes):
        pass

    def end_test(self, name, attributes):
        pass

    def start_keyword(self, name, attributes):
        self.on_start_keyword(name, attributes)

    def end_keyword(self, name, attributes):
        self.on_end_keyword(name, attributes)
