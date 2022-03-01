import typing
from typing import Dict, Iterator

T = typing.TypeVar("T")


class OrderedSet(typing.Generic[T]):
    """
    A simple ordered set with a regular dict as a basis.
    """

    def __init__(self, initial=None):
        self._dct: Dict[T, bool] = dict.fromkeys(initial or ())

    def add(self, obj: T) -> None:
        self._dct[obj] = True

    def discard(self, obj: T) -> None:
        self._dct.pop(obj, None)

    def __iter__(self) -> Iterator[T]:
        return iter(self._dct)

    def __contains__(self, obj: object) -> bool:
        return obj in self._dct

    def __bool__(self) -> bool:
        return bool(self._dct)

    def __len__(self) -> int:
        return len(self._dct)

    def __repr__(self) -> str:
        data = repr(list(self._dct)) if self._dct else ""
        return f"OrderedSet({data})"

    __str__ = __repr__
