import pytest


@pytest.fixture
def check_conda_yaml(datadir, data_regression):
    def check(name):
        from robocorp_code.deps import analyzer
        from robocorp_ls_core import uris
        from robocorp_ls_core.watchdog_wrapper import create_observer
        from robocorp_ls_core.workspace import Workspace

        ws = Workspace(str(datadir), create_observer("dummy", None))
        check_path = datadir / name
        uri = uris.from_fs_path(str(check_path / "conda.yaml"))
        doc = ws.get_document(uri, accept_from_file=True)

        data_regression.check(
            list(analyzer.Analyzer(doc.source, doc.path).iter_issues())
        )

    yield check


@pytest.mark.parametrize("name", ["check_python_version", "check_bad_conda"])
def test_python_version(check_conda_yaml, name):
    check_conda_yaml(name)
