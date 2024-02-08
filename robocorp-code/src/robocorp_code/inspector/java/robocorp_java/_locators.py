from typing import List, Optional, Union

from JABWrapper.context_tree import ContextNode, ContextTree, SearchElement

IntegerLocatorTypes = [
    "x",
    "y",
    "width",
    "height",
    "indexInParent",
    "ancestry",
    "childrentCount",
]


def _parse_locator(locator: str, strict_default=False):
    # TODO: from rpaframework, refactor if needed
    levels = locator.split(">")
    levels = [lvl.strip() for lvl in levels]
    searches = []
    for lvl in levels:
        conditions = lvl.split(" and ")
        lvl_search = []
        strict_mode = strict_default
        for cond in conditions:
            parts = cond.split(":", 1)
            if len(parts) == 1:
                parts = ["name", parts[0]]
            elif parts[0].lower() == "strict":
                strict_mode = bool(parts[1])
                continue
            elif parts[0] in IntegerLocatorTypes:
                try:
                    parts[1] = int(parts[1])
                except ValueError as err:
                    raise Exception(
                        "Locator '%s' needs to be of 'integer' type" % parts[0]
                    ) from err
            lvl_search.append(SearchElement(parts[0], parts[1], strict=strict_mode))
        searches.append(lvl_search)
    return searches


def find_elements_from_tree(
    context_tree: ContextTree,
    locator: str,
    index: Optional[int] = None,
) -> Union[ContextNode, List[ContextNode]]:
    # TODO: from rpaframework, refactor if needed
    searches = _parse_locator(locator)
    elements = []
    for lvl, search_elements in enumerate(searches):
        if lvl == 0:
            elements = context_tree.get_by_attrs(search_elements)
        else:
            sub_matches = []
            for elem in elements:
                matches = elem.get_by_attrs(search_elements)
                sub_matches.extend(matches)
            elements = sub_matches
    if index and len(elements) > (index + 1):
        raise AttributeError(
            "Locator '%s' returned only %s elements (can't index element at %s)"
            % (locator, len(elements), index)
        )
    return elements[index] if index else elements
