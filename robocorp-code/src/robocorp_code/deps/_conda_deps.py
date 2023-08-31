from dataclasses import dataclass
from typing import Dict, Iterator, Optional

from ._deps_protocols import _RangeTypedDict
from .conda_impl import conda_match_spec, conda_version


@dataclass
class CondaDepInfo:
    name: str  # The name of the dep (i.e.: python)
    value: str  # The full value of the dep (i.e.: python=3.7)
    version: str  # The version of the dep (as seen by conda: '3.7.*')
    dep_range: _RangeTypedDict


class CondaDeps:
    def __init__(self):
        self._deps: Dict[str, CondaDepInfo] = {}

    def add_dep(self, value: str, dep_range: _RangeTypedDict):
        """
        Args:
            value: This is the value found in the spec. Something as:
            'python==3.7'.
        """
        try:
            spec = conda_match_spec.parse_spec_str(value)

            # It may not have a version if it wasn't specified.
            version = spec.get("version", "*")
            if version.endswith("*"):
                version = version[:-1]
            name = spec["name"]
        except Exception:
            pass
        else:
            self._deps[name] = CondaDepInfo(name, value, version, dep_range)

    def get_dep_vspec(self, spec_name: str) -> Optional[conda_version.VersionSpec]:
        conda_dep_info = self._deps.get(spec_name)
        if conda_dep_info is None:
            return None
        vspec = conda_version.VersionSpec(conda_dep_info.version)
        return vspec

    def get_dep_range(self, spec_name: str) -> _RangeTypedDict:
        return self._deps[spec_name].dep_range

    def iter_conda_dep_infos(self) -> Iterator[CondaDepInfo]:
        yield from self._deps.values()
