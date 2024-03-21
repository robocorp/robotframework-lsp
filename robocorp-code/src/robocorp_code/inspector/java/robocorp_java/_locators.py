from typing import List, Optional, Sequence, Union

from JABWrapper.context_tree import (
    ContextNode,
    SearchElement,
)

IntegerLocatorTypes = [
    "x",
    "y",
    "width",
    "height",
    "row",
    "col",
    "indexInParent",
    "childrenCount",
    "ancestry",
]


def parse_locator(locator: str, strict_default=False):
    # TODO: from rpaframework, refactor if needed
    levels = locator.split(">")
    levels = [lvl.strip() for lvl in levels]
    searches = []
    for lvl in levels:
        conditions = lvl.split(" and ")
        lvl_search = []
        strict_mode = strict_default
        for condition in conditions:
            parts: Sequence[str] = condition.split(":", 1)
            name: str = parts[0] if len(parts) > 0 else ""
            value: Union[str, int] = parts[1] if len(parts) > 1 else ""
            if len(parts) == 1:
                parts = ["name", parts[0]]
            elif parts[0].lower() == "strict":
                strict_mode = bool(parts[1])
                continue
            elif parts[0] in IntegerLocatorTypes:
                try:
                    value = int(parts[1])
                except ValueError as err:
                    raise Exception(
                        "Locator '%s' needs to be of 'integer' type" % parts[0]
                    ) from err
            lvl_search.append(SearchElement(name, value, strict=strict_mode))
        searches.append(lvl_search)
    return searches


def find_elements_from_tree(
    context_tree: ContextNode,
    locator: str,
    index: Optional[int] = None,
) -> Union[ContextNode, List[ContextNode]]:
    # TODO: from rpaframework, refactor if needed
    searches = parse_locator(locator)
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
