from dataclasses import dataclass
from typing import Any, Iterator, List, Tuple

from .analyzer import _RangeTypedDict


@dataclass
class _PipDepInfo:
    name: str  # rpaframework
    extras: Any
    constraints: List[Tuple[str, str]]  # i.e.: [('==', '22.5.3')]
    marker: Any
    url: str
    requirement: str  #'rpaframework == 22.5.3'
    dep_range: _RangeTypedDict


class PipDeps:
    """
    pip references:
        pip._vendor.distlib.version.Matcher
        pip._vendor.distlib.util.parse_requirement
    """

    def __init__(self):
        self._pip_versions = {}

    def add_dep(self, value, as_range):
        from robocorp_code.deps.pip_impl.pip_distlib_util import parse_requirement

        req = parse_requirement(value)
        self._pip_versions[req.name] = _PipDepInfo(**req.__dict__, dep_range=as_range)

    def iter_pip_dep_infos(self) -> Iterator[_PipDepInfo]:
        yield from self._pip_versions.values()
