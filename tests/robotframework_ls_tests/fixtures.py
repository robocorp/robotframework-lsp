import threading
import pytest
from contextlib import contextmanager
import os
import logging
import sys
from robotframework_ls.options import USE_TIMEOUTS, NO_TIMEOUT
from robotframework_ls._utils import TimeoutError


log = logging.getLogger(__name__)

TIMEOUT = int(os.getenv("PYTEST_TIMEOUT", 7))
if not USE_TIMEOUTS:
    TIMEOUT = NO_TIMEOUT  # i.e.: None


def wait_for_condition(condition, msg=None, timeout=TIMEOUT, sleep=1 / 20.0):
    import time

    curtime = time.time()

    while True:
        if condition():
            break
        if timeout is not None and (time.time() - curtime > timeout):
            error_msg = "Condition not reached in %s seconds" % (timeout,)
            if msg is not None:
                error_msg += "\n"
                if callable(msg):
                    error_msg += msg()
                else:
                    error_msg += str(msg)

            raise TimeoutError(error_msg)
        time.sleep(sleep)


@pytest.fixture
def ws_root_path(tmpdir):
    return str(tmpdir.join("root"))


@contextmanager
def _communicate_lang_server(
    write_to, read_from, language_server_client_class=None, kwargs={}
):
    if language_server_client_class is None:
        from robotframework_ls_tests.language_server_client import _LanguageServerClient

        language_server_client_class = _LanguageServerClient

    from robotframework_ls.jsonrpc.streams import (
        JsonRpcStreamReader,
        JsonRpcStreamWriter,
    )

    w = JsonRpcStreamWriter(write_to, sort_keys=True)
    r = JsonRpcStreamReader(read_from)

    language_server = language_server_client_class(w, r, **kwargs)
    yield language_server

    if language_server.require_exit_messages:
        language_server.shutdown()
        language_server.exit()


@pytest.fixture
def language_server_tcp(log_file):
    """
    Starts a language server in the same process and communicates through tcp.
    """
    from robotframework_ls.__main__ import main

    import socket
    from robotframework_ls_tests.monitor_fixtures import dump_threads

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
        main(
            [
                "--tcp",
                "--host=127.0.0.1",
                "--port=0",
                "-vv",
                "--log-file=%s" % log_file,
            ],
            after_bind=after_bind,
        )
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

    if not finish_event.wait(TIMEOUT):
        dump_threads()
        raise AssertionError(
            "Language server thread did not exit in the available timeout."
        )


@pytest.fixture
def log_file(tmpdir):
    logs_dir = tmpdir.join("logs")
    logs_dir.mkdir()
    filename = str(logs_dir.join("robotframework_ls_tests.log"))
    sys.stderr.write("Logging subprocess to: %s" % (filename,))

    yield filename

    for name in os.listdir(str(logs_dir)):
        print("\n--- %s contents:" % (name,))
        with open(str(logs_dir.join(name)), "r") as stream:
            print(stream.read())


@pytest.fixture(autouse=True)
def config_logger(tmpdir):
    from robotframework_ls.__main__ import _configure_logger

    _configure_logger(2)


@pytest.fixture
def language_server_process(log_file):
    from robotframework_ls import __main__
    from robotframework_ls._utils import kill_process_and_subprocesses

    import subprocess

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
