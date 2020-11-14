import os

import pytest

from robocorp_ls_core.protocols import IConfigProvider
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from robocorp_code.protocols import IRcc


log = get_logger(__name__)


@pytest.fixture
def language_server_client_class():
    from robocorp_code_tests.robocode_language_server_client import (
        RobocorpLanguageServerClient,
    )

    return RobocorpLanguageServerClient


@pytest.fixture
def language_server_class():
    from robocorp_code.robocorp_language_server import RobocorpLanguageServer

    return RobocorpLanguageServer


@pytest.fixture
def main_module():
    from robocorp_code import __main__

    return __main__


@pytest.fixture
def rcc_location() -> str:
    from robocorp_code.rcc import download_rcc
    from robocorp_code.rcc import get_default_rcc_location

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


@pytest.fixture(scope="session")
def cases(tmpdir_factory) -> CasesFixture:
    basename = "res áéíóú"
    copy_to = str(tmpdir_factory.mktemp(basename))

    f = __file__
    original_resources_dir = os.path.join(os.path.dirname(f), "_resources")
    assert os.path.exists(original_resources_dir)

    return CasesFixture(copy_to, original_resources_dir)


@pytest.fixture
def config_provider(
    ws_root_path: str, rcc_location: str, ci_endpoint: str, rcc_config_location: str
):
    from robocorp_code.robocorp_config import RobocorpConfig
    from robocorp_ls_core.ep_providers import DefaultConfigurationProvider

    config = RobocorpConfig()

    config.update(
        {
            "robocorp": {
                "rcc": {
                    "location": rcc_location,
                    "endpoint": ci_endpoint,
                    "config_location": rcc_config_location,
                }
            }
        }
    )
    return DefaultConfigurationProvider(config)


@pytest.fixture
def rcc(config_provider: IConfigProvider, rcc_config_location: str) -> IRcc:
    from robocorp_code.rcc import Rcc

    rcc = Rcc(config_provider)
    # We don't want to track tests.
    for _i in range(2):
        # There's a bug in which the --do-not-track doesn't work the first time.
        result = rcc._run_rcc(
            "feedback identity --do-not-track --config".split() + [rcc_config_location],
            expect_ok=False,
        )
        assert result.success
        result_msg = result.result
        assert result_msg
        if "enabled" in result_msg:
            continue
        if "disabled" in result_msg:
            break
        raise AssertionError(f"Did not expect {result_msg}")
    else:
        raise AssertionError(f"Did not expect {result_msg}")

    return rcc


@pytest.fixture
def rcc_conda_installed(rcc: IRcc):
    result = rcc.check_conda_installed()
    assert result.success, r"Error: {result}"
