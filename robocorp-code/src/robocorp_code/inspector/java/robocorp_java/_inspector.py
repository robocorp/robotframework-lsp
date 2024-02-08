from typing import List, Optional, Union

from JABWrapper.context_tree import ContextNode, ContextTree
from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper, JavaWindow


class ElementInspector:
    def _start_event_pump(func, *args, **kwargs):
        def wrapper(self: "ElementInspector", *args, **kwargs):
            from ._event_pump import _EventPumpThread

            event_pump_thread = _EventPumpThread()
            event_pump_thread.start()
            jab_wrapper = event_pump_thread.get_wrapper()
            ret = func(self, jab_wrapper, *args, **kwargs)
            event_pump_thread.stop()
            return ret

        return wrapper

    @_start_event_pump
    def list_windows(self, jab_wrapper: JavaAccessBridgeWrapper) -> List[JavaWindow]:
        return jab_wrapper.get_windows()

    @_start_event_pump
    def collect_tree(
        self,
        jab_wrapper: JavaAccessBridgeWrapper,
        window: str,
        locator: Optional[str] = None,
    ) -> Union[ContextNode, List[ContextNode]]:
        jab_wrapper.switch_window_by_title(window)
        context_tree = ContextTree(jab_wrapper)
        if locator:
            from ._locators import find_elements_from_tree

            return find_elements_from_tree(context_tree, locator)
        return context_tree.root
