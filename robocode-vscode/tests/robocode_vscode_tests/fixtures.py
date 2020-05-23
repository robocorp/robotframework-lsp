import pytest


@pytest.fixture
def language_server_class():
    from robocode_vscode.robocode_language_server import RobocodeLanguageServer

    return RobocodeLanguageServer


@pytest.fixture
def main_module():
    from robocode_vscode import __main__

    return __main__
