from functools import wraps
from typing import Any, Callable, List, Optional, TypedDict, TypeVar, Union, cast

from JABWrapper.context_tree import ContextNode, ContextTree  # type: ignore
from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper, JavaWindow  # type: ignore
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


ColletedTreeTypedDict = TypedDict(
    "ColletedTreeTypedDict",
    {
        "matches": Union[ContextNode, List[ContextNode]],
        "tree": ContextNode,
    },
)

TFun = TypeVar("TFun", bound=Callable[..., Any])


class ElementInspector:
    def __init__(self) -> None:
        self._context: Optional[ContextNode] = None
        self._selected_window: Optional[str] = None

    @staticmethod
    def _start_event_pump(func: TFun) -> TFun:
        @wraps(func)
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

        return cast(TFun, wrapper)

    @_start_event_pump
    def list_windows(self, jab_wrapper: JavaAccessBridgeWrapper) -> List[JavaWindow]:
        return jab_wrapper.get_windows()

    def set_window(self, window: str) -> None:
        self._selected_window = window

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

            try:
                matches = find_elements_from_tree(self._context, locator)
            except AttributeError as e:
                log.error(e)
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
        matches: (ContextNode | List[ContextNode]) = []
        try:
            matches = find_elements_from_tree(self._context, locator)
        except AttributeError as e:
            log.error(e)
        return {"matches": matches, "tree": self._context}

    @_start_event_pump
    def collect_tree(
        self,
        jab_wrapper: JavaAccessBridgeWrapper,
        search_depth: int,
        locator: Optional[str] = None,
    ) -> ColletedTreeTypedDict:
        from ._errors import LocatorNotProvidedException, NoWindowSelected

        if not self._selected_window:
            raise NoWindowSelected("Select window first")

        jab_wrapper.switch_window_by_title(self._selected_window)

        if not self._context:
            return self._collect_from_root(jab_wrapper, locator, search_depth)
        else:
            if not locator:
                raise LocatorNotProvidedException(
                    "Locator needs to be provided to search the context"
                )
            return self._collect_from_context(jab_wrapper, locator, search_depth)
