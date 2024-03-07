from typing import Any, Callable, List, Optional, TypedDict, TypeVar, Union

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
        from robocorp_code.inspector.windows.robocorp_windows import WindowElement

        # TODO: the context now stores only the latest searched ContextNode and it's children
        # to the given search depth. When user traverses back up the tree we would need to have
        # the cached snapshot of all the previous searches in store.
        #
        # We need to store the whole tree here and always just update the tree from the locator
        # the user is picking and update the matched node and it's children.
        #
        # This will also need an update to the JavaAccessBridgeWrapper to have an API to update only
        # it and it's children (refresh is there, but does it respect search depth?).
        from ._event_pump import EventPumpThread

        self._context: Optional[ContextNode] = None
        self._selected_window: Optional[str] = None
        self._event_pump_thread: Optional[EventPumpThread] = None
        self._jab_wrapper: Optional[JavaAccessBridgeWrapper] = None
        self._window_obj: Optional[WindowElement] = None

    @property
    def event_pump_thread(self):
        if not self._event_pump_thread:
            from ._event_pump import EventPumpThread

            self._event_pump_thread = EventPumpThread()
            self._event_pump_thread.start()

        return self._event_pump_thread

    @property
    def jab_wrapper(self):
        try:
            if not self._jab_wrapper:
                self._jab_wrapper = self.event_pump_thread.get_wrapper()
            return self._jab_wrapper
        except Exception as e:
            log.error(e)
            self.event_pump_thread.stop()
            self._event_pump_thread = None
            self._jab_wrapper = None

    def list_windows(self) -> List[JavaWindow]:
        return self.jab_wrapper.get_windows()

    def set_window(self, window: str) -> None:
        from robocorp_code.inspector.windows.robocorp_windows import desktop

        self._selected_window = window
        self.jab_wrapper.switch_window_by_title(self._selected_window)
        self._window_obj = desktop().find_window(
            f"{window}",
            search_depth=1,
            foreground=True,
            move_cursor_to_center=False,
        )

    def bring_app_to_frontend(self):
        import time

        self._window_obj.update_geometry()
        if not self._window_obj.has_valid_geometry():
            self._window_obj.restore_window()
            # compensating because of Windows animations
            time.sleep(0.25)
        self._window_obj.foreground_window(move_cursor_to_center=False)
        time.sleep(0.2)

    def _collect_from_root(
        self,
        locator: Optional[str],
        search_depth=1,
    ) -> ColletedTreeTypedDict:
        self._context = ContextTree(self.jab_wrapper, search_depth).root
        matches: Union[ContextNode, List[ContextNode]] = []
        if locator:
            from ._locators import find_elements_from_tree

            try:
                matches = find_elements_from_tree(self._context, locator)
            except AttributeError as e:
                log.error(e)
        return {"matches": matches, "tree": self._context}

    def _collect_from_context(
        self, locator: str, search_depth=1
    ) -> ColletedTreeTypedDict:
        from ._errors import ContextNotAvailable, NoMatchingLocatorException
        from ._locators import find_elements_from_tree

        # The JavaAccessBridgeWrapper object needs to be inserted into the context as the
        # object has to be recreated every time we do a new query
        # TODO: update the ContextTree to introduce the API for this
        if not self._context:
            raise ContextNotAvailable(
                "Cannot search from context as it hasn't been created yet"
            )
        match = find_elements_from_tree(self._context, locator)

        node = match[0] if isinstance(match, List) and len(match) > 0 else match
        if not isinstance(node, ContextNode):
            raise NoMatchingLocatorException(f"No matching locator for {locator}")

        # TODO: update the ContextNode API to have refresh function that takes a new context and the max depth
        node._jab_wrapper = self.jab_wrapper
        node._max_depth = search_depth + node.ancestry
        node.refresh()

        matches: (ContextNode | List[ContextNode]) = []
        try:
            matches = find_elements_from_tree(self._context, locator)
        except AttributeError as e:
            log.error(e)
        return {"matches": matches, "tree": node}

    def collect_tree(
        self,
        search_depth: int,
        locator: Optional[str] = None,
    ) -> ColletedTreeTypedDict:
        from ._errors import NoWindowSelected

        if not self._selected_window:
            raise NoWindowSelected("Select window first")

        self.jab_wrapper.switch_window_by_title(self._selected_window)

        if not self._context or not locator:
            return self._collect_from_root(locator, search_depth)
        else:
            return self._collect_from_context(locator, search_depth)
