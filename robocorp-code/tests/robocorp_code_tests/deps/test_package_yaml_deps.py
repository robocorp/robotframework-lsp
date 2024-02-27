from typing import Iterator

import pytest
from robocorp_ls_core.protocols import IDocument


def get_package_yaml_doc(datadir, name) -> IDocument:
    from robocorp_ls_core import uris
    from robocorp_ls_core.watchdog_wrapper import create_observer
    from robocorp_ls_core.workspace import Workspace

    ws = Workspace(str(datadir), create_observer("dummy", None))
    check_path = datadir / name
    uri = uris.from_fs_path(str(check_path / "package.yaml"))
    doc = ws.get_document(uri, accept_from_file=True)
    assert doc
    return doc


@pytest.fixture
def check_package_yaml(datadir, data_regression, cached_conda_cloud) -> Iterator:
    def check(name):
        from robocorp_code.vendored_deps.package_deps.analyzer import (
            PackageYamlAnalyzer,
        )

        doc = get_package_yaml_doc(datadir, name)

        analyzer = PackageYamlAnalyzer(
            doc.source, doc.path, conda_cloud=cached_conda_cloud
        )
        data_regression.check(list(analyzer.iter_package_yaml_issues()))

    yield check


@pytest.mark.parametrize(
    "name",
    [
        "check_bad_package_yaml",
        "check_bad_python_version",
        "check_deps_from_conda",
        "check_bad_version",
        "check_bad_op",
    ],
)
def test_package_yaml(check_package_yaml, name: str, patch_pypi_cloud) -> None:
    check_package_yaml(name)
