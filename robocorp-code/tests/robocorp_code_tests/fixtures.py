import os

import pytest

from robocorp_ls_core.protocols import IConfigProvider
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from robocorp_code.protocols import IRcc, ActionResult


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
    # There's a bug in which the --do-not-track doesn't work the first time.
    result = rcc._run_rcc(
        "configure identity --do-not-track --config".split() + [rcc_config_location]
    )
    assert result.success
    result_msg = result.result
    assert result_msg
    if "disabled" not in result_msg:
        raise AssertionError(f"Did not expect {result_msg}")

    return rcc


@pytest.fixture
def rcc_conda_installed(rcc: IRcc):
    result = rcc.check_conda_installed()
    assert result.success, r"Error: {result}"


_WS_INFO = (
    {
        "id": "workspace_id_1",
        "name": "CI workspace",
        "orgId": "affd282c8f9fe",
        "orgName": "My Org Name",
        "orgShortName": "654321",
        "shortName": "123456",  # Can be some generated number or something provided by the user.
        "state": "active",
        "url": "http://url1",
    },
    {
        "id": "workspace_id_2",
        "name": "My Other workspace",
        "orgId": "affd282c8f9fe",
        "orgName": "My Org Name",
        "orgShortName": "1234567",
        "shortName": "7654321",
        "state": "active",
        "url": "http://url2",
    },
)

_PACKAGE_INFO_WS_2: dict = {}

_PACKAGE_INFO_WS_1: dict = {
    "activities": [
        {"id": "452", "name": "Package Name 1"},
        {"id": "453", "name": "Package Name 2"},
    ]
}


class RccPatch(object):
    def __init__(self, monkeypatch):
        from robocorp_code.rcc import Rcc

        self.monkeypatch = monkeypatch
        self._current_mock = self.mock_run_rcc_default
        self._original = Rcc._run_rcc
        self._package_info_ws_1 = _PACKAGE_INFO_WS_1
        self.custom_handler = None

    def mock_run_rcc(self, args, *starargs, **kwargs) -> ActionResult:
        return self._current_mock(args, *starargs, **kwargs)

    def mock_run_rcc_default(self, args, *sargs, **kwargs) -> ActionResult:
        import json
        import copy

        if self.custom_handler is not None:
            ret = self.custom_handler(args, *sargs, **kwargs)
            if ret is not None:
                return ret

        if args[:4] == ["cloud", "workspace", "--workspace", "workspace_id_1"]:
            # List packages for workspace 1
            return ActionResult(
                success=True, message=None, result=json.dumps(self._package_info_ws_1)
            )

        if args[:4] == ["cloud", "workspace", "--workspace", "workspace_id_2"]:
            # List packages for workspace 2
            return ActionResult(
                success=True, message=None, result=json.dumps(_PACKAGE_INFO_WS_2)
            )

        if args[:3] == ["cloud", "workspace", "--config"]:
            # List workspaces
            workspace_info = _WS_INFO
            return ActionResult(
                success=True, message=None, result=json.dumps(workspace_info)
            )

        if args[:3] == ["cloud", "push", "--directory"]:
            if args[4:8] == ["--workspace", "workspace_id_1", "--robot", "2323"]:
                return ActionResult(success=True)
            if args[4:8] == ["--workspace", "workspace_id_1", "--robot", "453"]:
                return ActionResult(success=True)

        if args[:5] == ["cloud", "new", "--workspace", "workspace_id_1", "--robot"]:
            # Submit a new package to ws 1
            cp = copy.deepcopy(self._package_info_ws_1)
            cp["activities"].append({"id": "2323", "name": args[5]})
            self._package_info_ws_1 = cp

            return ActionResult(
                success=True,
                message=None,
                result="Created new robot named {args[5]} with identity 2323.",
            )

        if args[:4] == ["config", "credentials", "-j", "--verified"]:
            return ActionResult(
                success=True,
                message=None,
                result=json.dumps(
                    [
                        {
                            "account": "robocorp-code",
                            "identifier": "001",
                            "endpoint": "https://endpoint.foo.bar",
                            "secret": "123...",
                            "verified": 1605525807,
                        }
                    ]
                ),
            )

        raise AssertionError(f"Unexpected args: {args}")

    def mock_run_rcc_should_not_be_called(self, args, *sargs, **kwargs):
        raise AssertionError(
            "This should not be called at this time (data should be cached)."
        )

    def apply(self) -> None:
        from robocorp_code.rcc import Rcc

        self.monkeypatch.setattr(Rcc, "_run_rcc", self.mock_run_rcc)

    def disallow_calls(self) -> None:
        self._current_mock = self.mock_run_rcc_should_not_be_called


@pytest.fixture
def rcc_patch(monkeypatch):
    return RccPatch(monkeypatch)
