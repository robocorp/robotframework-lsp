import os

import pytest

from robocode_ls_core.robotframework_log import get_logger


log = get_logger(__name__)


@pytest.fixture
def language_server_class():
    from robocode_vscode.robocode_language_server import RobocodeLanguageServer

    return RobocodeLanguageServer


@pytest.fixture
def main_module():
    from robocode_vscode import __main__

    return __main__


@pytest.fixture
def rcc_location() -> str:
    from robocode_vscode.rcc import download_rcc
    from robocode_vscode.rcc import get_default_rcc_location

    location = get_default_rcc_location()
    download_rcc(location, force=False)
    return location


@pytest.fixture
def ci_endpoint() -> str:
    ci_endpoint = os.environ.get("CI_ENDPOINT")
    if ci_endpoint is None:
        raise AssertionError("CI_ENDPOINT env variable must be specified for tests.")
    return ci_endpoint


@pytest.fixture
def ci_credentials() -> str:
    ci_credentials = os.environ.get("CI_CREDENTIALS")
    if ci_credentials is None:
        raise AssertionError("ci_credentials env variable must be specified for tests.")
    return ci_credentials


@pytest.fixture
def rcc_config_location(tmpdir) -> str:
    config_dir = tmpdir.join("config")
    os.makedirs(str(config_dir))
    return str(config_dir.join("config_test.yaml"))
