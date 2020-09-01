import pytest


@pytest.fixture
def language_server_client_class():
    from robocorp_ls_core.unittest_tools.language_server_client import (
        LanguageServerClient,
    )

    return LanguageServerClient


@pytest.fixture
def language_server_class():
    from example_vscode.example_vscode_language_server import (
        ExampleVSCodeLanguageServer,
    )

    return ExampleVSCodeLanguageServer


@pytest.fixture
def main_module():
    from example_vscode import __main__

    return __main__
