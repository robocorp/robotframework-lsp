import typing
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, TypedDict, Union

from robocorp_code.deps.pip_impl.pip_packaging_version import LegacyVersion, Version
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)

# Interesting:
# https://github.com/python-poetry/poetry/blob/master/src/poetry/repositories/pypi_repository.py

VersionStr = str
Versions = Union[LegacyVersion, Version]
UrlDescription = str
UrlStr = str


@dataclass
class ReleaseData:
    version: Versions
    version_str: VersionStr

    def __lt__(self, other):
        return self.version < other.version


class PyPiInfoTypedDict(TypedDict):
    description: str
    description_content_type: str
    package_url: str
    project_urls: Dict[UrlDescription, UrlStr]

    # Info for the latest version
    # The constraints. i.e.: ['rpaframework-windows (>=7.3.2,<8.0.0) ; sys_platform == "win32"']
    # Something as ">=3.7,<4.0"
    requires_dist: List[str]
    requires_python: str
    version: VersionStr


class PackageData:
    def __init__(self, package_name: str, info: PyPiInfoTypedDict) -> None:
        self.package_name = package_name
        self._info = info

        self._releases: Dict[str, ReleaseData] = {}

    def add_release(self, version_str: VersionStr, release_info: List[dict]) -> None:
        """
        Args:
            version_str: The version we have info on.
            release_info: For each release we may have a list of files available.
        """
        from robocorp_code.deps.pip_impl import pip_packaging_version

        version = pip_packaging_version.parse(version_str)
        self._releases[version_str] = ReleaseData(version, version_str)

    @property
    def latest_version(self) -> VersionStr:
        return self._info["version"]

    def iter_versions_newer_than(self, version: Versions) -> Iterator[ReleaseData]:
        for release_data in self._releases.values():
            if release_data.version > version:
                yield release_data


class PyPiCloud:
    def __init__(self) -> None:
        self._cached: Dict[str, PackageData] = {}
        self._base_url = "https://pypi.org"

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, base_url: str) -> None:
        if self._base_url != base_url:
            self._base_url = base_url
            self._cached.clear()

    def _get_json_from_cloud(self, url: str) -> Optional[dict]:
        try:
            return typing.cast(dict, self._cached[url])
        except KeyError:
            pass

        import requests

        try:
            info = requests.get(url)
            self._cached[url] = info.json()
        except Exception as e:
            log.info(f"Unable to get url (as json): {url}. Error: {e}")
            return None

        return typing.cast(dict, self._cached[url])

    def get_versions_newer_than(
        self, package_name: str, version: Union[Versions, VersionStr]
    ) -> List[VersionStr]:
        """
        Args:
            package_name: The name of the package
            version: The minimum version (versions returned must be > than this one).

        Returns:
            A sorted list containing the versions > than the one passed (the last
            entry is the latest version).
        """

        if isinstance(version, VersionStr):
            from robocorp_code.deps.pip_impl import pip_packaging_version

            version = pip_packaging_version.parse(version)

        base_url = self._base_url
        data = self._get_json_from_cloud(f"{base_url}/pypi/{package_name}/json")
        if not data:
            return []
        releases = data["releases"]
        package_data = PackageData(package_name, data["info"])
        if releases and isinstance(releases, dict):
            for release_number, release_info in releases.items():
                package_data.add_release(release_number, release_info)

        self._cached[package_name] = package_data
        return [
            x.version_str
            for x in sorted(package_data.iter_versions_newer_than(version))
        ]
