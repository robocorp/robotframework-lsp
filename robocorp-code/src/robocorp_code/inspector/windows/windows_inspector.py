import enum
import typing
from typing import (
    Any,
    Callable,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    TypedDict,
    Union,
)

from robocorp_ls_core.callbacks import Callback

if typing.TYPE_CHECKING:
    from robocorp_code.inspector.windows.robocorp_windows import (
        ControlElement,
        WindowElement,
    )
    from robocorp_code.inspector.windows.robocorp_windows._iter_tree import (
        ControlTreeNode,
    )


ControlLocatorInfoTypedDict = TypedDict(
    "ControlLocatorInfoTypedDict",
    {
        "control": str,
        "class": str,
        "name": str,
        "automation_id": str,
        "handle": int,
        "left": int,
        "right": int,
        "top": int,
        "bottom": int,
        "width": int,
        "height": int,
        "xcenter": int,
        "ycenter": int,
        # Relative information based on the query.
        # May be used to recreate the tree-structure
        # afterwards (as APIs usually provide
        # a flat list).
        "depth": int,
        "child_pos": int,
        "path": str,
    },
)


WindowLocatorInfoTypedDict = TypedDict(
    "WindowLocatorInfoTypedDict",
    {
        # Same as control
        "control": str,
        "class": str,
        "name": str,
        "automation_id": str,
        "handle": int,
        "left": int,
        "right": int,
        "top": int,
        "bottom": int,
        "width": int,
        "height": int,
        "xcenter": int,
        "ycenter": int,
        # Note: depth/child_pos/path don't make sense for
        # top-level windows.
        # Additional only in Window
        "pid": int,
        "executable": str,
    },
)


class MatchesAndHierarchyTypedDict(TypedDict):
    # A list with the `path` items matched (these are the ones that the
    # locator matched)
    matched_paths: List[str]
    # This includes all the entries found along with the full hierarchy
    # to reach the matched entries.
    hierarchy: List[ControlLocatorInfoTypedDict]


def _get_from_obj(el: Union["WindowElement", "ControlElement"], dct_name: str) -> Any:
    from robocorp_code.inspector.windows.robocorp_windows._ui_automation_wrapper import (
        LocationInfo,
    )

    attr_name = dct_name
    target: Union["WindowElement", "ControlElement", "LocationInfo"] = el
    if attr_name == "control":
        attr_name = "control_type"
    elif attr_name == "class":
        attr_name = "class_name"

    elif dct_name in ("depth", "child_pos", "path"):
        target = el.location_info

    return getattr(target, attr_name)


def to_window_info(w: "WindowElement") -> WindowLocatorInfoTypedDict:
    ret = {}
    for dct_name in WindowLocatorInfoTypedDict.__annotations__:
        ret[dct_name] = _get_from_obj(w, dct_name)
    return typing.cast(WindowLocatorInfoTypedDict, ret)


def to_control_info(el: "ControlElement") -> ControlLocatorInfoTypedDict:
    ret = {}
    for dct_name in ControlLocatorInfoTypedDict.__annotations__:
        ret[dct_name] = _get_from_obj(el, dct_name)
    return typing.cast(ControlLocatorInfoTypedDict, ret)


class IOnPickCallback(typing.Protocol):
    def __call__(self, locator_info_tree: List[ControlLocatorInfoTypedDict]):
        """
        Args:
            locator_info_tree: This will provide the structure from parent to
            child containing the nodes to make the pick (i.e.: the first element
            is the first element inside the window and the last element is
            the leaf element picked).
        """

    def register(
        self, callback: Callable[[List[ControlLocatorInfoTypedDict]], Any]
    ) -> None:
        pass

    def unregister(
        self, callback: Callable[[List[ControlLocatorInfoTypedDict]], Any]
    ) -> None:
        pass


class _State(enum.Enum):
    default = 1
    picking = 2
    highlighting = 3


def to_matches_and_hierarchy(
    parent: "ControlElement", matched_controls: Sequence["ControlElement"]
) -> MatchesAndHierarchyTypedDict:
    from robocorp_code.inspector.windows.robocorp_windows._inspect import (
        build_parent_hierarchy,
    )

    hierarchy: List[ControlLocatorInfoTypedDict] = []
    matched_paths: List[str] = []

    # Keep the paths already seen.
    already_in_hierarchy: Set[str] = set()
    for control in matched_controls:
        path = control.location_info.path
        assert path
        matched_paths.append(path)

        for node in build_parent_hierarchy(control, parent):
            if node.path not in already_in_hierarchy:
                already_in_hierarchy.add(node.path)
                hierarchy.append(to_control_info(node.control))

    return {"matched_paths": matched_paths, "hierarchy": hierarchy}


class WindowsInspector:
    def __init__(self) -> None:
        from robocorp_code.inspector.windows.robocorp_windows._inspect import (
            ElementInspector,
        )

        # Called as: self.on_pick([ControlLocatorInfoTypedDict])
        self.on_pick: IOnPickCallback = Callback()
        self._element_inspector: Optional[ElementInspector] = None
        self._state = _State.default

    def dispose(self):
        if self._element_inspector is not None:
            self._element_inspector.dispose()
            self._element_inspector = None
        self._state = _State.default

    def set_window_locator(self, window_locator: str):
        """
        Sets the base window which should be inspected.

        Args:
            window_locator: The locator of the window which should be inspected.

        Raises:
            ElementNotFound if the window matching the given locator wasn't found.
        """
        self.dispose()

        from robocorp_code.inspector.windows.robocorp_windows import find_window
        from robocorp_code.inspector.windows.robocorp_windows._inspect import (
            ElementInspector,
        )

        # No timeout. The windows must be there already.
        pick_window = find_window(window_locator, timeout=0)
        self._element_inspector = ElementInspector(pick_window)

    def _on_internal_pick(self, found: List["ControlTreeNode[ControlElement]"]):
        converted: List[ControlLocatorInfoTypedDict] = []
        for node in found:
            converted.append(to_control_info(node.control))
        self.on_pick(converted)

    def reset_to_default_state(self):
        """
        Will stop any pick or highlight currently in place.
        """
        if self._state == _State.picking:
            self.stop_pick()

        elif self._state == _State.highlighting:
            self.stop_highlight()

    def start_pick(self) -> None:
        """
        Starts picking so that when the cursor is hovered over an item of the
        UI the `on_pick` callback is triggered.

        Args:
            window_locator: The locator of the window which should be picked.

        Raises:
            ElementNotFound if the window matching the given locator wasn't found.
        """
        if self._element_inspector is None:
            return

        self.reset_to_default_state()
        self._state = _State.picking
        self._element_inspector.start_picking(self._on_internal_pick)

    def stop_pick(self) -> None:
        """
        Stops picking.
        """
        if self._state == _State.picking:
            if self._element_inspector is not None:
                self._element_inspector.stop_picking()
            self._state = _State.default

    def start_highlight(
        self,
        locator: str,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ) -> MatchesAndHierarchyTypedDict:
        """
        Starts highlighting the matches given by the locator specified.

        Args:
            locator: The locator whose matches should be highlighted.

        Returns:
            The matches found as a flattened list (the tree hierarchy
            may be rebuilt based on the `path` or `depth` and `child_pos`).
        """
        if not self._element_inspector:
            raise RuntimeError(
                "Unable to make match because `set_window_locator` was not previously used to set the window of interest."
            )

        matched_controls = self._element_inspector.start_highlight(
            locator,
            search_depth=search_depth,
            timeout=0,
            search_strategy=search_strategy,
        )

        parent = self._element_inspector.control_element
        return to_matches_and_hierarchy(parent, matched_controls)

    def stop_highlight(self) -> None:
        """
        Stops highlighting matches.
        """
        if self._state == _State.highlighting:
            if self._element_inspector is not None:
                self._element_inspector.stop_highlight()
            self._state = _State.default

    def list_windows(self) -> List[WindowLocatorInfoTypedDict]:
        from robocorp_code.inspector.windows import robocorp_windows

        windows = robocorp_windows.find_windows("regex:.*", search_depth=1)
        return [to_window_info(w) for w in windows]

    def collect_tree(
        self,
        locator: str,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ) -> MatchesAndHierarchyTypedDict:
        if not self._element_inspector:
            raise RuntimeError(
                "Unable to collect tree because `set_window_locator` was not previously used to set the window of interest."
            )

        matched_controls: List[
            "ControlElement"
        ] = self._element_inspector.control_element.find_many(
            locator,
            search_depth=search_depth,
            search_strategy=search_strategy,
            timeout=0,
        )
        return to_matches_and_hierarchy(
            self._element_inspector.control_element, matched_controls
        )
