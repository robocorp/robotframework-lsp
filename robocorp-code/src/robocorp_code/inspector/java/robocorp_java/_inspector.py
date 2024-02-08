from typing import List

from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper, JavaWindow


class ElementInspector:
    def __init__(self):
        from ._event_pump import _EventPumpThread

        self._pump_thread = _EventPumpThread()

    def _start_pump(func, *args, **kwargs):
        def wrapper(self: "ElementInspector", *args, **kwargs):
            self._pump_thread.start()
            jab_wrapper = self._pump_thread.get_wrapper()
            ret = func(self, jab_wrapper, *args, **kwargs)
            self._pump_thread.stop()
            return ret

        return wrapper

    @_start_pump
    def list_windows(self, jab_wrapper: JavaAccessBridgeWrapper) -> List[JavaWindow]:
        return jab_wrapper.get_windows()
