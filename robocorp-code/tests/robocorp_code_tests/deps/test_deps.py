from typing import Iterator

import pytest
from robocorp_ls_core.protocols import IDocument


def get_conda_yaml_doc(datadir, name) -> IDocument:
    from robocorp_ls_core import uris
    from robocorp_ls_core.watchdog_wrapper import create_observer
    from robocorp_ls_core.workspace import Workspace

    ws = Workspace(str(datadir), create_observer("dummy", None))
    check_path = datadir / name
    uri = uris.from_fs_path(str(check_path / "conda.yaml"))
    doc = ws.get_document(uri, accept_from_file=True)
    assert doc
    return doc


@pytest.fixture
def check_conda_yaml(datadir, data_regression) -> Iterator:
    def check(name):
        from robocorp_code.deps.analyzer import Analyzer

        doc = get_conda_yaml_doc(datadir, name)

        analyzer = Analyzer(doc.source, doc.path)
        data_regression.check(list(analyzer.iter_issues()))

    yield check


@pytest.mark.parametrize(
    "name",
    [
        "check_python_version",
        "check_bad_conda",
        "check_bad_version",
        "check_bad_version2",
    ],
)
def test_python_version(check_conda_yaml, name: str, patch_pypi_cloud) -> None:
    check_conda_yaml(name)


def test_hover_conda_yaml_pip_package(datadir, patch_pypi_cloud):
    from robocorp_code.deps.analyzer import Analyzer

    doc = get_conda_yaml_doc(datadir, "check_python_version")

    analyzer = Analyzer(doc.source, doc.path)
    pip_dep = analyzer.find_pip_dep_at(14, 17)
    assert pip_dep is not None
    assert pip_dep.name == "rpaframework"


def test_hover_conda_yaml_conda_package(datadir, patch_pypi_cloud):
    from robocorp_code.deps.analyzer import Analyzer

    doc = get_conda_yaml_doc(datadir, "check_python_version")

    analyzer = Analyzer(doc.source, doc.path)
    conda_dep = analyzer.find_conda_dep_at(10, 7)
    assert conda_dep is not None
    assert conda_dep.name == "python"


def test_hover_conda_yaml_rpaframework(
    datadir, data_regression, patch_pypi_cloud, cached_conda_cloud
):
    from robocorp_code.deps.pypi_cloud import PyPiCloud
    from robocorp_code.hover import hover_on_conda_yaml

    doc = get_conda_yaml_doc(datadir, "check_python_version")

    pypi_cloud = PyPiCloud()
    data_regression.check(
        hover_on_conda_yaml(doc, 14, 17, pypi_cloud, cached_conda_cloud)
    )


def test_conda_version_spec_api():
    from robocorp_code.deps.analyzer import check_version
    from robocorp_code.deps.conda_impl import conda_version

    v = conda_version.VersionSpec("22.1.3")
    op = v.get_matcher(">=22")[1]
    assert op(v)

    v24 = conda_version.VersionSpec("24")
    assert op(v24)

    v21 = conda_version.VersionSpec("21")
    assert not op(v21)

    v = conda_version.VersionSpec("3.8")
    op = v.get_matcher(">=3.8")[1]
    assert op(v)

    assert check_version(conda_version.VersionSpec("21"), ">=21")


def test_pypi_cloud(patch_pypi_cloud) -> None:
    from robocorp_code.deps.pypi_cloud import PyPiCloud

    pypi_cloud = PyPiCloud()

    versions = pypi_cloud.get_versions_newer_than("rpaframework", "22.1")
    assert versions == [
        "22.1.1",
        "22.2.0",
        "22.2.1",
        "22.2.2",
        "22.2.3",
        "22.3.0",
        "22.4.0",
        "22.5.0",
        "22.5.1",
        "22.5.2",
        "22.5.3",
        "23.0.0",
        "23.1.0",
        "23.2.0",
        "23.2.1",
        "23.3.0",
        "23.4.0",
        "23.5.0",
        "23.5.1",
        "23.5.2",
        "24.0.0",
        "24.1.0",
        "24.1.1",
        "24.1.2",
    ]


def test_pypi_cloud_jq(patch_pypi_cloud) -> None:
    from robocorp_code.deps.pypi_cloud import PyPiCloud

    pypi_cloud = PyPiCloud()

    versions = pypi_cloud.get_versions_newer_than("jq", "1.3")
    # Note: versions "1.5.0a1", "1.5.0" are marked as uploaded after
    # the latest release marked (1.4.1) and aren't shown due to that.
    assert versions == ["1.4.0", "1.4.1"]
