import typing
from typing import Any, Callable, List, Optional, TypedDict, cast

from JABWrapper.context_tree import ContextNode  # type: ignore
from JABWrapper.jab_wrapper import JavaWindow  # type: ignore
from robocorp_ls_core.callbacks import Callback
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
    "LocatorNodeInfoTypedDict",
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
        "ancestry": int,
    },
)


class MatchesAndHierarchyTypedDict(TypedDict):
    # A list with the nodes matched (these are the ones that the
    # locator matched)
    matched_paths: List[str]
    # This includes all the entries found along with the full hierarchy
    # to reach the matched entries.
    hierarchy: List[LocatorNodeInfoTypedDict]


class IOnPickCallback(typing.Protocol):
    def __call__(self, locator_info_tree: List[dict]):
        pass

    def register(self, callback: Callable[[Any], Any]) -> None:
        pass

    def unregister(self, callback: Callable[[Any], Any]) -> None:
        pass


def to_window_info(java_window: JavaWindow) -> JavaWindowInfoTypedDict:
    ret = {}
    for dct_name in JavaWindowInfoTypedDict.__annotations__:
        ret[dct_name] = getattr(java_window, dct_name)
    return cast(JavaWindowInfoTypedDict, ret)


def to_locator_info(context_node: ContextNode) -> LocatorNodeInfoTypedDict:
    ret = {}
    for dct_name in LocatorNodeInfoTypedDict.__annotations__:
        if (dct_name) == "ancestry":
            ret["ancestry"] = getattr(context_node, dct_name)
        else:
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
    return {"matched_paths": matches, "hierarchy": hierarchy}


class JavaInspector:
    def __init__(self):
        from robocorp_code.inspector.java.robocorp_java._inspector import (
            ElementInspector,
        )

        self._inspector = ElementInspector()
        self.on_pick: IOnPickCallback = Callback()
        # make sure we have the access bridge dll inside the environment
        self.__inject_access_bridge_path()
        self.__enable_switch()

    @staticmethod
    def __inject_access_bridge_path():
        # TODO: change the Exceptions to something more specific
        import os

        # check if RC_JAVA_ACCESS_BRIDGE_DLL is set
        java_access_bridge_path = os.environ.get("RC_JAVA_ACCESS_BRIDGE_DLL", None)
        if not java_access_bridge_path:
            # if not 2 check the JAVA_HOME is set
            java_home = os.environ.get("JAVA_HOME", None)
            if not java_home:
                # this would be bad
                raise Exception(
                    "Java wasn't detected. JAVA_HOME environment variable is not set."
                )
            java_access_bridge_path = os.path.join(
                java_home, "jre", "bin", "WindowsAccessBridge-64.dll"
            )
            if os.path.exists(java_access_bridge_path):
                # good
                # inject env variable
                os.environ["RC_JAVA_ACCESS_BRIDGE_DLL"] = java_access_bridge_path
                log.info(
                    "=== JAVA: RC_JAVA_ACCESS_BRIDGE_DLL:", java_access_bridge_path
                )
                return
            raise Exception("Java Access DLL was not found")

    @staticmethod
    def __enable_switch():
        import os
        import subprocess

        java_home = os.environ.get("JAVA_HOME", None)
        try:
            if not java_home:
                raise Exception(
                    "Java wasn't detected. JAVA_HOME environment variable is not set."
                )
            jabswitch = os.path.join(java_home, "jre", "bin", "jabswitch.exe")
            if not os.path.exists(jabswitch):
                raise Exception("Could not find the jabswitch")
            output = subprocess.check_output([jabswitch, "-enable"])
            log.info("=== JAVA: enabling jabswitch:", output)
        except Exception as e:
            log.info("=== JAVA: jabswitch exception:", e)
            pass

    def list_opened_applications(self) -> List[JavaWindowInfoTypedDict]:
        """
        List all available Java applications.
        """
        windows = self._inspector.list_windows()
        return [to_window_info(window) for window in windows]

    def set_window_locator(self, window: str) -> None:
        """
        Set the current Java window user chose.
        """
        log.info(f"=== JAVA: Selected window: {window}")
        self._inspector.set_window(window)

    def collect_tree(
        self, search_depth=1, locator: Optional[str] = None
    ) -> MatchesAndHierarchyTypedDict:
        """
        Collect the app element hierarchy from the locator match with given search depth.
        """
        matches_and_hierarchy = self._inspector.collect_tree(search_depth, locator)
        log.info(
            f"=== JAVA: collect_tree: matches_and_hierarchy:", matches_and_hierarchy
        )
        return to_matches_and_hierarchy(matches_and_hierarchy)

    def start_pick(self) -> None:
        pass

    def stop_pick(self) -> None:
        pass

    def start_highlight(
        self,
        locator: str,
        search_depth: int = 8,
    ) -> None:
        """
        Can we use the same Windows highlight implementation?

        This API should get the locator and find the element based on that locator.
        The found element has x, y coordinates plus the width and the heigth fields
        that we can use to calculate the borders for the highlited area.
        """
        pass

    def stop_highlight(self) -> None:
        """
        Dispose the highlight thread.
        """
        pass
