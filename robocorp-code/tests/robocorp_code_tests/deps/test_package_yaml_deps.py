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


def test_hover_package_pip_package(datadir, patch_pypi_cloud, cached_conda_cloud):
    from robocorp_code.vendored_deps.package_deps.analyzer import PackageYamlAnalyzer

    doc = get_package_yaml_doc(datadir, "check_python_version")

    analyzer = PackageYamlAnalyzer(doc.source, doc.path, cached_conda_cloud)
    pip_dep = analyzer.find_pip_dep_at(16, 17)
    assert pip_dep is not None
    assert pip_dep.name == "rpaframework"


def test_hover_package_yaml_conda_package(
    datadir, patch_pypi_cloud, cached_conda_cloud
):
    from robocorp_code.vendored_deps.package_deps.analyzer import PackageYamlAnalyzer

    doc = get_package_yaml_doc(datadir, "check_python_version")

    analyzer = PackageYamlAnalyzer(doc.source, doc.path, cached_conda_cloud)
    conda_dep = analyzer.find_conda_dep_at(13, 7)
    assert conda_dep is not None
    assert conda_dep.name == "python"


def test_hover_package_yaml_rpaframework(
    datadir, data_regression, patch_pypi_cloud, cached_conda_cloud
):
    from robocorp_code.hover import hover_on_package_yaml
    from robocorp_code.vendored_deps.package_deps.pypi_cloud import PyPiCloud

    doc = get_package_yaml_doc(datadir, "check_python_version")

    pypi_cloud = PyPiCloud()
    data_regression.check(
        hover_on_package_yaml(doc, 16, 17, pypi_cloud, cached_conda_cloud)
    )
