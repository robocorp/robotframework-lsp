import threading
import pytest

try:
    TimeoutError = TimeoutError  # @ReservedAssignment
except NameError:

    class TimeoutError(RuntimeError):  # @ReservedAssignment
        pass


TIMEOUT = 5


def wait_for_condition(condition, msg=None, timeout=TIMEOUT, sleep=0.05):
    import time

    curtime = time.time()

    while True:
        if condition():
            break
        if time.time() - curtime > timeout:
            error_msg = "Condition not reached in %s seconds" % (timeout,)
            if msg is not None:
                error_msg += "\n"
                if callable(msg):
                    error_msg += msg()
                else:
                    error_msg += str(msg)

            raise TimeoutError(error_msg)
        time.sleep(sleep)


@pytest.fixture(autouse=True)
def _log_for_tests():
    from robotframework_ls.__main__ import _configure_logger

    _configure_logger(2)


@pytest.fixture
def ws_root_path(tmpdir):
    return str(tmpdir.join("root"))


@pytest.fixture
def language_server():
    from robotframework_ls.__main__ import main
    from pyls_jsonrpc.streams import JsonRpcStreamReader
    import socket
    from robotframework_ls_tests.language_server_client import _LanguageServerClient

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
    r = JsonRpcStreamReader(s.makefile("rb"))

    yield _LanguageServerClient(w, r)

    w.write(
        {"jsonrpc": "2.0", "id": 1, "method": "shutdown",}
    )
    w.write(
        {"jsonrpc": "2.0", "id": 1, "method": "exit",}
    )
    assert finish_event.wait(5)
