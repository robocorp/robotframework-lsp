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
    def __init__(self) -> None:
        self._context: Optional[ContextNode] = None

    def _start_event_pump(func, *args, **kwargs):
        def wrapper(self, *args, **kwargs):
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

    def _collect_from_root(
        self,
        jab_wrapper: JavaAccessBridgeWrapper,
        locator: Optional[str],
        search_depth=1,
    ) -> ColletedTreeTypedDict:
        self._context = ContextTree(jab_wrapper, search_depth).root
        matches: Union[ContextNode, List[ContextNode]] = []
        if locator:
            from ._locators import find_elements_from_tree

            matches = find_elements_from_tree(self._context, locator)
        return {"matches": matches, "tree": self._context}

    def _collect_from_context(
        self, jab_wrapper: JavaAccessBridgeWrapper, locator: str, search_depth=1
    ) -> ColletedTreeTypedDict:
        from threading import RLock

        from ._errors import ContextNotAvailable, NoMatchingLocatorException
        from ._locators import find_elements_from_tree

        # The JavaAccessBridgeWrapper object needs to be inserted into the context as the
        # object has to be recreated every time we do a new query
        # TODO: update the ContextTree to introduce the API for this
        if not self._context:
            raise ContextNotAvailable(
                "Cannot search from context as it hasn't been created yet"
            )
        self._context._jab_wrapper = jab_wrapper
        match = find_elements_from_tree(self._context, locator)
        node = match[0] if isinstance(match, List) and len(match) > 0 else match
        if not isinstance(node, ContextNode):
            raise NoMatchingLocatorException(f"No matching locator for {locator}")
        self._context = ContextNode(
            jab_wrapper,
            node.context,
            RLock(),
            node.ancestry,
            True,
            search_depth + node.ancestry,
        )
        matches = find_elements_from_tree(self._context, locator)
        return {"matches": matches, "tree": self._context}

    @_start_event_pump
    def collect_tree(
        self,
        jab_wrapper: JavaAccessBridgeWrapper,
        window: str,
        search_depth: int,
        locator: Optional[str] = None,
    ) -> ColletedTreeTypedDict:
        jab_wrapper.switch_window_by_title(window)

        if not self._context:
            return self._collect_from_root(jab_wrapper, locator, search_depth)
        else:
            return self._collect_from_context(jab_wrapper, locator, search_depth)
