import time
import re
import threading
from typing import Any, Callable, List, Optional, Tuple, TypedDict, cast, Protocol

from JABWrapper.context_tree import ContextNode  # type: ignore
from JABWrapper.jab_wrapper import JavaWindow  # type: ignore

from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.java.robocorp_java._inspector import ColletedTreeTypedDict


log = get_logger(__name__)

MAX_ELEMENTS_TO_HIGHLIGHT = 20

RESOLUTION_PIXEL_RATIO = 2

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


class IOnPickCallback(Protocol):
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


def to_geometry_str(match_string: str) -> Optional[Tuple[int, int, int, int]]:
    pattern = (
        r"x:(?P<x>-?\d+)\s+y:(?P<y>-?\d+).+width:(?P<width>\d+).+height:(?P<height>\d+)"
    )
    values = re.search(pattern, match_string)
    if values:
        left = int(values.group("x"))
        top = int(values.group("y"))
        right = int(values.group("width")) + left
        bottom = int(values.group("height")) + top
        return (
            left * RESOLUTION_PIXEL_RATIO,
            top * RESOLUTION_PIXEL_RATIO,
            right * RESOLUTION_PIXEL_RATIO,
            bottom * RESOLUTION_PIXEL_RATIO,
        )
    else:
        return None


def to_geometry_node(node: LocatorNodeInfoTypedDict):
    left = int(node["x"])
    top = int(node["y"])
    right = int(node["width"]) + left
    bottom = int(node["height"]) + top
    return (
        left * RESOLUTION_PIXEL_RATIO,
        top * RESOLUTION_PIXEL_RATIO,
        right * RESOLUTION_PIXEL_RATIO,
        bottom * RESOLUTION_PIXEL_RATIO,
    )


def to_element_history_filtered(hierarchy: list):
    # deal only with the remaining elements
    current_number_of_children = 0
    root_index = -1
    reconstructed_tree: List[List[dict]] = []

    for index, elem in enumerate(hierarchy):
        if current_number_of_children == 0:
            root_index += 1
            current_number_of_children = 0
            for ind in range(root_index, len(hierarchy)):
                current_number_of_children = hierarchy[ind]["childrenCount"]
                if current_number_of_children > 0:
                    root_index = ind
                    break

            if index > 0:
                current_number_of_children -= 1

        else:
            current_number_of_children -= 1

        ls = []
        if len(reconstructed_tree) > root_index:
            ls.extend(reconstructed_tree[root_index])
        ls.append(elem)
        reconstructed_tree.append(ls)
    return reconstructed_tree


def to_unique_locator(elem: LocatorNodeInfoTypedDict):
    locator = f"role:{elem['role']}"
    if elem["name"]:
        locator += f' and name:{elem["name"]}'
    if elem["description"]:
        locator += f' and description:{elem["description"]}'
    if elem["indexInParent"]:
        locator += f' and indexInParent:{elem["indexInParent"]}'
    if elem["childrenCount"]:
        locator += f' and childrenCount:{elem["childrenCount"]}'
    if elem["states"]:
        locator += f' and states:{elem["states"]}'
    if elem["x"]:
        locator += f' and x:{elem["x"]}'
    if elem["y"]:
        locator += f' and y:{elem["y"]}'
    if elem["width"]:
        locator += f' and width:{elem["width"]}'
    if elem["height"]:
        locator += f' and height:{elem["height"]}'
    return locator


class JavaInspector:
    def __init__(self):
        import threading
        from robocorp_code.inspector.java.robocorp_java._inspector import (
            ElementInspector,
        )
        from robocorp_code.inspector.java.highlighter import TkHandlerThread

        self._element_inspector = ElementInspector()
        self._tk_handler_thread: TkHandlerThread = TkHandlerThread()
        self._tk_handler_thread.start()

        self._timer_thread: Optional[threading.Timer] = None

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
        windows = self._element_inspector.list_windows()
        windows_list = []
        for window in windows:
            win = to_window_info(window)
            if not win["title"]:
                continue
            windows_list.append(win)
        return windows_list

    def set_window_locator(self, window: str) -> None:
        """
        Set the current Java window user chose.
        """
        log.info(f"=== JAVA: Selected window: {window}")
        self._element_inspector.set_window(window)
        self._element_inspector.bring_app_to_frontend()

    def collect_tree(
        self, search_depth=1, locator: Optional[str] = None
    ) -> MatchesAndHierarchyTypedDict:
        """
        Collect the app element hierarchy from the locator match with given search depth.
        """
        matches_and_hierarchy = self._element_inspector.collect_tree(
            search_depth, locator
        )
        log.info(
            f"=== JAVA: collect_tree: matches_and_hierarchy:", matches_and_hierarchy
        )
        return to_matches_and_hierarchy(matches_and_hierarchy)

    def collect_tree_from_root(
        self, search_depth=1, locator: Optional[str] = None
    ) -> MatchesAndHierarchyTypedDict:
        """
        Collect the app element hierarchy from the locator match with given search depth.
        """
        matches_and_hierarchy = self._element_inspector.collect_tree_from_root(
            search_depth, locator
        )
        log.info(
            f"=== JAVA: collect_tree_from_root: matches_and_hierarchy:",
            matches_and_hierarchy,
        )
        return to_matches_and_hierarchy(matches_and_hierarchy)

    # search_tree_for_element - elem as param - (node_index, (left, top, right, bottom))
    def search_tree_for_element(
        self,
        elem_to_find: Tuple,
        locator: str,
        ancestry: list,
        depth: int,
    ) -> list:
        _, geometry = elem_to_find
        left, top, _, _ = geometry
        try:
            if depth >= 3:
                log.info("######## HIT DEPTH !!!")
                return

            log.info("######## TESTING LOCATOR:", locator)
            log.info("######## TESTING DEPTH:", depth)
            tree = self.collect_tree(search_depth=1, locator=locator)
            log.info("######## LOCATOR TREE:", tree)
            time.sleep(2)

            if not len(tree["hierarchy"]):
                return
            for elem in reversed(tree["hierarchy"]):
                if str(elem["x"]) == str(left) and str(elem["y"]) == str(top):
                    log.info("@@@@@@@@ FOUND ELEMENT !!!", elem)
                    log.info("@@@@@@@@ FOUND ANCESTRY !!!", ancestry)
                    return
                locator = to_unique_locator(elem)
                ancestry.append(elem)
                depth = depth + 1
                self.search_tree_for_element(
                    elem_to_find=elem_to_find,
                    locator=locator,
                    ancestry=ancestry,
                    depth=depth,
                )
            return
        except Exception:
            return

    def start_pick(self) -> None:
        try:
            app_tree = self.collect_tree_from_root(search_depth=200, locator="role:.*")
            if not len(app_tree["matched_paths"]):
                raise ValueError()
        except Exception:
            raise Exception("Could not collect the tree elements. Rejecting picker!")

        # log.info("@@@@@@ Matches:", len(app_tree["matched_paths"]))
        # for index, hist in enumerate(app_tree["hierarchy"]):
        #     log.info("@@@@@@ Hist:", index, hist)

        # tree_geometries = [ (node_index, (left, top, right, bottom) ) ]
        tree_geometries: List[Tuple[int, Tuple]] = []
        for node_index, node in enumerate(app_tree["hierarchy"]):
            geometry = to_geometry_node(node)
            if geometry is not None:
                tree_geometries.append((node_index, geometry, node))

        # on_pick_wrapper - callback function that has the elem as param - (node_index, (left, top, right, bottom), node)
        def on_pick_wrapper(picked_elem: Tuple[int, Tuple, dict]):
            return_ancestry = []
            try:
                ######################################### ORIGINAL
                # node_index, _ = elem
                # for index, node_ancestry in enumerate(app_tree_nodes_with_ancestries):
                #     if index == node_index:
                #         return_ancestry = node_ancestry
                #         break
                #########################################
                picked_node_index, _, picked_node = picked_elem
                log.info("@@@@@@ NODE TO TEST:", picked_node)
                # filter out not needed elements from the hierarchy based on ancestry
                filtered_tree = []
                for node in app_tree["hierarchy"]:
                    if node["ancestry"] <= picked_node["ancestry"]:
                        log.info("@@@@@@ Adding:", node)
                        filtered_tree.append(node)
                log.info("@@@@@@ FILTERED TREE:", filtered_tree)
                for i, node in enumerate(filtered_tree):
                    log.info("@@@@@@ --- NODE:", i, node)
                    if node == picked_node:
                        # changing the index based on the filtered elements
                        picked_node_index = i
                log.info("@@@@@@ --- PICKED INDEX:", picked_node_index)
                # create the ancestries
                nodes_with_ancestries = to_element_history_filtered(filtered_tree)
                for index, node_ancestry in enumerate(nodes_with_ancestries):
                    log.info("@@@@@@ NODE W/ ANCESTRY:", index, node_ancestry)
                    if index == picked_node_index:
                        return_ancestry = node_ancestry
                        break
                log.info("@@@@@@ RETURNING ANCESTRY:", return_ancestry)
            except Exception:
                return_ancestry = []
            self.on_pick(return_ancestry)

        self._element_inspector.start_picker(
            tk_handler_thread=self._tk_handler_thread,
            tree_geometries=tree_geometries,
            on_pick=on_pick_wrapper,
        )

    def stop_pick(self) -> None:
        self._element_inspector.stop_picker()

    def start_highlight(
        self,
        locator: str,
        search_depth: int = 8,
    ) -> None:
        self._element_inspector.bring_app_to_frontend()

        # kill the TK thread
        self._tk_handler_thread.quitloop()
        self._tk_handler_thread.destroy_tk_handler()
        # recreate the TK thread
        self._tk_handler_thread.create()
        self._tk_handler_thread.loop()

        try:
            matches_and_hierarchy = self.collect_tree(
                search_depth=search_depth, locator=locator
            )
        except Exception:
            matches_and_hierarchy = {"hierarchy": [], "matched_paths": []}

        nodes = matches_and_hierarchy["hierarchy"]

        # skipping displaying highlights if number of matches exceeds limit
        if len(nodes) > MAX_ELEMENTS_TO_HIGHLIGHT:
            return matches_and_hierarchy

        rects = []
        for element in nodes:
            geometry = to_geometry_node(element)
            if geometry:
                left, top, right, bottom = geometry
                rects.append((left, top, right, bottom))

        self._tk_handler_thread.set_rects(rects)

        # killing the highlight after a period of time
        # TODO: this might be
        def kill_highlight():
            self._tk_handler_thread.set_rects([])
            if self._timer_thread:
                self._timer_thread.cancel()
                self._timer_thread = None

        self._timer_thread = threading.Timer(3, kill_highlight)
        self._timer_thread.start()

    def stop_highlight(self) -> None:
        """
        Dispose the highlight thread.
        """
        self._tk_handler_thread.set_rects([])
        if self._timer_thread:
            self._timer_thread.cancel()
            self._timer_thread = None
