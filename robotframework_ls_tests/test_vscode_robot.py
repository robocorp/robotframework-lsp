import socket
import threading
import pytest


@pytest.fixture
def language_server():
    from robotframework_ls.__main__ import main

    class _LanguageServerConfig(object):

        address = None

    config = _LanguageServerConfig()
    start_event = threading.Event()
    finish_event = threading.Event()

    def after_bind(server):
        address = server.socket.getsockname()
        config.address = address
        start_event.set()

    def start_language_server():
        main(["--tcp", "--host=127.0.0.1", "--port=0"], after_bind=after_bind)
        finish_event.set()

    t = threading.Thread(target=start_language_server, name="Language Server", args=())
    t.start()

    assert start_event.wait(5)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(config.address)
    from pyls_jsonrpc.streams import JsonRpcStreamWriter

    w = JsonRpcStreamWriter(s.makefile("wb"), sort_keys=True)

    yield w

    w.write(
        {"jsonrpc": "2.0", "id": 1, "method": "shutdown",}
    )
    w.write(
        {"jsonrpc": "2.0", "id": 1, "method": "exit",}
    )
    assert finish_event.wait(5)


def test_robotframework_ls(language_server):
    language_server.write(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",}
    )
