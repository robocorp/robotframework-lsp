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
