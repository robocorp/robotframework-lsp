import threading
import pytest
from contextlib import contextmanager
import os
import logging

try:
    TimeoutError = TimeoutError  # @ReservedAssignment
except NameError:

    class TimeoutError(RuntimeError):  # @ReservedAssignment
        pass


log = logging.getLogger(__name__)

TIMEOUT = int(os.getenv("PYTEST_TIMEOUT", 5))


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


@contextmanager
def _communicate_lang_server(write_to, read_from):
    from robotframework_ls_tests.language_server_client import _LanguageServerClient

    from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

    w = JsonRpcStreamWriter(write_to, sort_keys=True)
    r = JsonRpcStreamReader(read_from)

    language_server = _LanguageServerClient(w, r)
    yield language_server

    if language_server.require_exit_messages:
        language_server.shutdown()
        language_server.exit()


@pytest.fixture
def language_server_tcp():
    """
    Starts a language server in the same process and communicates through tcp.
    """
    from robotframework_ls.__main__ import main

    import socket

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

    assert start_event.wait(TIMEOUT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(config.address)
    write_to = s.makefile("wb")
    read_from = s.makefile("rb")
    with _communicate_lang_server(write_to, read_from) as lang_server_client:
        yield lang_server_client

    assert finish_event.wait(TIMEOUT)


@pytest.fixture
def language_server_process(tmpdir):
    from robotframework_ls import __main__
    from robotframework_ls._utils import kill_process_and_subprocesses

    import subprocess
    import sys

    log_file = str(tmpdir.join("robotframework_ls_tests.log"))
    log.debug("Logging subprocess to: %s", log_file)
    language_server_process = subprocess.Popen(
        [sys.executable, "-u", __main__.__file__, "-vv", "--log-file=%s" % log_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    assert language_server_process.returncode is None
    yield language_server_process
    if language_server_process.returncode is None:
        kill_process_and_subprocesses(language_server_process.pid)

    print("--- %s contents:" % (log_file,))
    with open(log_file, "r") as stream:
        print(stream.read())


@pytest.fixture
def language_server_io(language_server_process):
    """
    Starts a language server in a new process and communicates through stdin/stdout streams.
    """
    write_to = language_server_process.stdin
    read_from = language_server_process.stdout

    with _communicate_lang_server(write_to, read_from) as lang_server_client:
        yield lang_server_client


@pytest.fixture(params=["io", "tcp"])
def language_server(request):
    if request.param == "io":
        return request.getfixturevalue("language_server_io")
    else:
        return request.getfixturevalue("language_server_tcp")
