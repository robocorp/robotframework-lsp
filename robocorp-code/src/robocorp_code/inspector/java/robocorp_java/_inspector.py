from typing import List, Optional, TypedDict, Union

from JABWrapper.context_tree import ContextNode, ContextTree
from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper, JavaWindow

ColletedTreeTypedDict = TypedDict(
    "ColletedTreeTypedDict",
    {
        "matches": Union[ContextNode, List[ContextNode]],
        "tree": ContextNode,
    },
)


class ElementInspector:
    def _start_event_pump(func, *args, **kwargs):
        def wrapper(self: "ElementInspector", *args, **kwargs):
            from ._event_pump import EventPumpThread

            event_pump_thread = EventPumpThread()
            event_pump_thread.start()
            try:
                jab_wrapper = event_pump_thread.get_wrapper()
                ret = func(self, jab_wrapper, *args, **kwargs)
            finally:
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
        search_depth: int,
        locator: Optional[str] = None,
    ) -> ColletedTreeTypedDict:
        jab_wrapper.switch_window_by_title(window)
        context_tree = ContextTree(jab_wrapper, search_depth)
        matches: Union[ContextNode, List[ContextNode]] = []
        if locator:
            from ._locators import find_elements_from_tree

            matches = find_elements_from_tree(context_tree, locator)
        return {"matches": matches, "tree": context_tree.root}
