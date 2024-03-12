import time
from typing import List, Tuple

matches_and_hierarchy = {
    "hierarchy": [
        (
            0,
            {
                "name": "Logisim: main of Untitled",
                "role": "frame",
                "description": "",
                "states": "enabled,focusable,visible,showing,active,resizable",
                "indexInParent": -1,
                "childrenCount": 1,
                "x": 1334,
                "y": 308,
                "width": 640,
                "height": 480,
                "ancestry": 0,
            },
        ),
        (
            1,
            {
                "name": "",
                "role": "root pane",
                "description": "",
                "states": "enabled,focusable,visible,showing,opaque",
                "indexInParent": 0,
                "childrenCount": 2,
                "x": 1342,
                "y": 339,
                "width": 624,
                "height": 441,
                "ancestry": 1,
            },
        ),
        (
            2,
            {
                "name": "",
                "role": "panel",
                "description": "",
                "states": "enabled,focusable",
                "indexInParent": 0,
                "childrenCount": 0,
                "x": -1,
                "y": -1,
                "width": -1,
                "height": -1,
                "ancestry": 2,
            },
        ),
        (
            3,
            {
                "name": "",
                "role": "layered pane",
                "description": "",
                "states": "enabled,focusable,visible,showing",
                "indexInParent": 1,
                "childrenCount": 2,
                "x": 1342,
                "y": 339,
                "width": 624,
                "height": 441,
                "ancestry": 2,
            },
        ),
        (
            4,
            {
                "name": "",
                "role": "panel",
                "description": "",
                "states": "enabled,focusable,visible,showing,opaque",
                "indexInParent": 0,
                "childrenCount": 2,
                "x": 1342,
                "y": 360,
                "width": 624,
                "height": 420,
                "ancestry": 3,
            },
        ),
        (
            5,
            {
                "name": "",
                "role": "panel",
                "description": "",
                "states": "enabled,focusable,visible,showing,opaque",
                "indexInParent": 0,
                "childrenCount": 2,
                "x": 1342,
                "y": 388,
                "width": 624,
                "height": 392,
                "ancestry": 4,
            },
        ),
        (
            6,
            {
                "name": "",
                "role": "panel",
                "description": "",
                "states": "enabled,focusable,visible,showing,opaque",
                "indexInParent": 1,
                "childrenCount": 2,
                "x": 1342,
                "y": 360,
                "width": 624,
                "height": 28,
                "ancestry": 4,
            },
        ),
        (
            7,
            {
                "name": "",
                "role": "menu bar",
                "description": "",
                "states": "enabled,focusable,visible,showing,opaque",
                "indexInParent": 1,
                "childrenCount": 6,
                "x": 1342,
                "y": 339,
                "width": 624,
                "height": 21,
                "ancestry": 3,
            },
        ),
        (
            8,
            {
                "name": "File",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 0,
                "childrenCount": 14,
                "x": 1342,
                "y": 339,
                "width": 27,
                "height": 19,
                "ancestry": 4,
            },
        ),
        (
            9,
            {
                "name": "Edit",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 1,
                "childrenCount": 17,
                "x": 1369,
                "y": 339,
                "width": 29,
                "height": 19,
                "ancestry": 4,
            },
        ),
        (
            10,
            {
                "name": "Project",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 2,
                "childrenCount": 19,
                "x": 1398,
                "y": 339,
                "width": 45,
                "height": 19,
                "ancestry": 4,
            },
        ),
        (
            11,
            {
                "name": "Simulate",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 3,
                "childrenCount": 12,
                "x": 1443,
                "y": 339,
                "width": 55,
                "height": 19,
                "ancestry": 4,
            },
        ),
        (
            12,
            {
                "name": "Window",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 4,
                "childrenCount": 8,
                "x": 1498,
                "y": 339,
                "width": 53,
                "height": 19,
                "ancestry": 4,
            },
        ),
        (
            13,
            {
                "name": "Help",
                "role": "menu",
                "description": "",
                "states": "enabled,focusable,visible,showing,selectable",
                "indexInParent": 5,
                "childrenCount": 5,
                "x": 1551,
                "y": 339,
                "width": 33,
                "height": 19,
                "ancestry": 4,
            },
        ),
    ]
}


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
                current_number_of_children = hierarchy[ind][1]["childrenCount"]
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


def find_node_history(hierarchy: List[Tuple[int, dict]], node_index: int):
    tree: List[List[dict]] = []

    for elem in hierarchy:
        elem_index, elem_node = elem
        print("-" * 75)
        print("Working on:", elem)
        if elem_index == node_index:
            return tree


# to_element_history_filtered(matches_and_hierarchy["hierarchy"])

tree = find_node_history(matches_and_hierarchy["hierarchy"], 8)
print("=" * 75)
for n in tree:
    print("-", n)
