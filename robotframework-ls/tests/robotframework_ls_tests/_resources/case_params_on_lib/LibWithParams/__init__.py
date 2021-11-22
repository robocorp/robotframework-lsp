class LibWithParams(object):
    def __init__(self, some_param):
        self.some_param = some_param
        if some_param == "bar":
            self.bar_method = self._some_method
        elif some_param == "foo":
            self.foo_method = self._some_method
        else:
            raise AssertionError(f"Unexpected: {some_param}")

    def _some_method(self):
        return
