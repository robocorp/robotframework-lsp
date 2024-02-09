from typing import List, Optional, TypedDict, cast

from JABWrapper.context_tree import ContextNode
from JABWrapper.jab_wrapper import JavaWindow
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.java.robocorp_java._inspector import ColletedTreeTypedDict

log = get_logger(__name__)

JavaWindowInfoTypedDict = TypedDict(
    "JavaWindowInfoTypedDict",
    {
        "pid": int,
        "hwnd": int,
        "title": str,
    },
)

LocatorNodeInfoTypedDict = TypedDict(
    "LocatorNoneInfoTypedDict",
    {
        "name": str,
        "role": str,
        "description": str,
        "states": str,
        "indexInParent": int,
        "childrenCount": int,
        "x": int,
        "y": int,
        "width": int,
        "height": int,
    },
)


class MatchesAndHierarchyTypedDict(TypedDict):
    # A list with the nodes matched (these are the ones that the
    # locator matched)
    matched_paths: List[str]
    # This includes all the entries found along with the full hierarchy
    # to reach the matched entries.
    hierarchy: List[LocatorNodeInfoTypedDict]


def to_window_info(java_window: JavaWindow) -> JavaWindowInfoTypedDict:
    ret = {}
    for dct_name in JavaWindowInfoTypedDict.__annotations__:
        ret[dct_name] = getattr(java_window, dct_name)
    return cast(JavaWindowInfoTypedDict, ret)


def to_locator_info(context_node: ContextNode) -> LocatorNodeInfoTypedDict:
    ret = {}
    for dct_name in LocatorNodeInfoTypedDict.__annotations__:
        ret[dct_name] = getattr(context_node.context_info, dct_name)
    return cast(LocatorNodeInfoTypedDict, ret)


def to_matches_and_hierarchy(
    matches_and_hierarchy: ColletedTreeTypedDict,
) -> MatchesAndHierarchyTypedDict:
    matches = (
        [str(matches_and_hierarchy["matches"])]
        if type(matches_and_hierarchy["matches"]) == ContextNode
        else [str(match) for match in matches_and_hierarchy["matches"]]
    )
    hierarchy = [to_locator_info(node) for node in matches_and_hierarchy["tree"]]
    return {"matches": matches, "hierarchy": hierarchy}


class JavaInspector:
    def __init__(self):
        from robocorp_code.inspector.java.robocorp_java._inspector import (
            ElementInspector,
        )

        self._inspector = ElementInspector()

    def list_windows(self) -> List[JavaWindowInfoTypedDict]:
        windows = self._inspector.list_windows()
        return [to_window_info(window) for window in windows]

    def collect_tree(
        self, window: str, search_depth: int = 8, locator: Optional[str] = None
    ) -> MatchesAndHierarchyTypedDict:
        log.info(f"Collect tree from locator: {locator}")

        matches_and_hierarchy = self._inspector.collect_tree(
            window, search_depth, locator
        )
        return to_matches_and_hierarchy(matches_and_hierarchy)
