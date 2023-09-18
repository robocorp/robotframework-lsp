import traceback


class _Callback(object):
    on_exception = None

    def __init__(self):
        self._callbacks = []

    def register(self, callback):
        self._callbacks.append(callback)

    def __call__(self, *args, **kwargs):
        for c in self._callbacks:
            try:
                c(*args, **kwargs)
            except:
                # If something goes bad calling some callback, just print
                # it and keep on going to the next one.
                traceback.print_exc()
                on_exception = self.on_exception
                if on_exception is not None:
                    on_exception()


class DebugListener(object):
    ROBOT_LISTENER_API_VERSION = 3

    on_start_suite = _Callback()
    on_end_suite = _Callback()
    on_start_test = _Callback()
    on_end_test = _Callback()
    on_log_message = _Callback()
    on_message = _Callback()

    def start_suite(self, data, result):
        self.on_start_suite(data, result)

    def end_suite(self, data, result):
        self.on_end_suite(data, result)

    def start_test(self, data, result):
        self.on_start_test(data, result)

    def end_test(self, data, result):
        self.on_end_test(data, result)

    def log_message(self, message):
        self.on_log_message(message)

    def message(self, message):
        self.on_message(message)

    # def start_keyword(self, data, result):
    #     # This would be nice, but it's not currently supported.
    #
    # def end_keyword(self, data, result):
    #     # This would be nice, but it's not currently supported.


class DebugListenerV2(object):
    ROBOT_LISTENER_API_VERSION = 2

    on_start_keyword = _Callback()
    on_end_keyword = _Callback()
    on_start_suite = _Callback()
    on_end_suite = _Callback()
    on_start_test = _Callback()
    on_end_test = _Callback()
    on_log_message = _Callback()
    on_message = _Callback()

    def start_suite(self, name, attributes):
        self.on_start_suite(name, attributes)

    def end_suite(self, name, attributes):
        self.on_end_suite(name, attributes)

    def start_test(self, name, attributes):
        self.on_start_test(name, attributes)

    def end_test(self, name, attributes):
        self.on_end_test(name, attributes)

    def start_keyword(self, name, attributes):
        self.on_start_keyword(name, attributes)

    def end_keyword(self, name, attributes):
        self.on_end_keyword(name, attributes)

    def log_message(self, message):
        self.on_log_message(message)

    def message(self, message):
        self.on_message(message)


def install_rf_stream_connection(write_message):
    try:
        from robot_out_stream import RFStream
    except ImportError:
        from robotframework_ls import import_robot_out_stream

        import_robot_out_stream()

        from robot_out_stream import RFStream

    def write_str(s):
        write_message({"type": "event", "event": "rfStream", "body": {"msg": s}})

    kwargs = {"--dir": "None", "__write__": write_str}
    rfstream = RFStream(**kwargs)

    DebugListenerV2.on_start_suite.register(rfstream.start_suite)
    DebugListenerV2.on_end_suite.register(rfstream.end_suite)

    DebugListenerV2.on_start_test.register(rfstream.start_test)
    DebugListenerV2.on_end_test.register(rfstream.end_test)

    DebugListenerV2.on_start_keyword.register(rfstream.start_keyword)
    DebugListenerV2.on_end_keyword.register(rfstream.end_keyword)

    DebugListenerV2.on_log_message.register(rfstream.log_message)
    DebugListenerV2.on_message.register(rfstream.message)
