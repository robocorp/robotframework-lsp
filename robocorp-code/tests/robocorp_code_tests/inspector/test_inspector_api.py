import pytest


class _DummyLanguageServer:
    def dispose(self):
        pass


@pytest.fixture
def dummy_language_server():
    ret = _DummyLanguageServer()
    yield ret
    ret.dispose()


@pytest.fixture
def inspector_server_manager(dummy_language_server):
    from robocorp_code.inspector.inspector_server_manager import InspectorServerManager

    return InspectorServerManager(dummy_language_server)


def test_inspector_api_integrated(inspector_server_manager):
    """
    This test actually creates a server manager which will launch the inspector
    API in a different process and interact with it as needed.
    """
    inspector_api_client = inspector_server_manager.get_inspector_api_client()
    assert inspector_api_client is not None
    assert inspector_api_client.send_sync_message("echo", {"arg": 1})["result"] == [
        "echo",
        1,
    ]
    assert inspector_api_client.send_sync_message("not_there", {})["error"][
        "message"
    ].startswith("Method Not Found")

    message_matcher = inspector_api_client.send_async_message("echo", {"arg": 1})
    assert message_matcher.event.wait(10)
    assert message_matcher.msg["result"] == [
        "echo",
        1,
    ]


def test_inspector_api_raw():
    """
    This test uses the inspector API directly in the current process.
    """
    from io import BytesIO

    from robocorp_code.inspector.inspector_api import InspectorApi

    read_from = BytesIO()
    write_to = BytesIO()
    inspector_api = InspectorApi(read_from, write_to)
    assert inspector_api.m_echo(1) == ("echo", 1)
