from contextlib import contextmanager
import os
import sys
import threading
from robocorp_ls_core.options import USE_TIMEOUTS, NO_TIMEOUT
import pytest
from typing import Optional

TIMEOUT: Optional[float]
_curr_pytest_timeout = os.getenv("PYTEST_TIMEOUT")
if _curr_pytest_timeout:
    TIMEOUT = float(_curr_pytest_timeout) / 3.0
else:
    TIMEOUT = 20
if not USE_TIMEOUTS:
    TIMEOUT = NO_TIMEOUT  # i.e.: None


def wait_for_test_condition(condition, msg=None, timeout=TIMEOUT, sleep=1 / 20.0):
    from robocorp_ls_core.basic import wait_for_condition as w

    return w(condition, msg=msg, timeout=timeout, sleep=sleep)


@pytest.fixture
def ws_root_path(tmpdir):
    return str(tmpdir.join("root"))


@pytest.fixture(scope="function", autouse=True)
def fix_dircache_directory(tmpdir, monkeypatch):
    #: :type monkeypatch: _pytest.monkeypatch.MonkeyPatch
    monkeypatch.setenv("ROBOCORP_CODE_USER_HOME", str(tmpdir))


@pytest.fixture(autouse=True)
def config_logger(tmpdir):
    from robocorp_ls_core.robotframework_log import configure_logger

    configure_logger("test", 2, None)


@contextmanager
def communicate_lang_server(
    write_to, read_from, language_server_client_class=None, kwargs={}
):
    if language_server_client_class is None:
        from robocorp_ls_core.unittest_tools.language_server_client import (
            LanguageServerClient,
        )

        language_server_client_class = LanguageServerClient

    from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamWriter
    from robocorp_ls_core.jsonrpc.streams import JsonRpcStreamReader

    w = JsonRpcStreamWriter(write_to, sort_keys=True)
    r = JsonRpcStreamReader(read_from)

    language_server = language_server_client_class(w, r, **kwargs)
    try:
        yield language_server
    finally:
        if language_server.require_exit_messages:
            language_server.shutdown()
            language_server.exit()


@contextmanager
def start_language_server_tcp(
    log_file, main_method, language_server_class, language_server_client_class
):
    """
    Starts a language server in the same process and communicates through tcp.

    Yields a language server client.
    """
    import socket
    from robocorp_ls_core.unittest_tools.monitor import dump_threads

    class _LanguageServerConfig(object):

        address = None

    config = _LanguageServerConfig()
    start_event = threading.Event()
    finish_event = threading.Event()
    language_server_instance_final = []

    def after_bind(server):
        address = server.socket.getsockname()
        config.address = address
        start_event.set()

    def start_language_server():
        def new_language_server_class(*args, **kwargs):
            language_server_instance = language_server_class(*args, **kwargs)
            language_server_instance_final.append(language_server_instance)
            return language_server_instance

        main_method(
            [
                "--tcp",
                "--host=127.0.0.1",
                "--port=0",
                "-vv",
                "--log-file=%s" % log_file,
            ],
            after_bind=after_bind,
            language_server_class=new_language_server_class,
        )
        finish_event.set()

    t = threading.Thread(target=start_language_server, name="Language Server", args=())
    t.start()

    assert start_event.wait(TIMEOUT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(config.address)
    write_to = s.makefile("wb")
    read_from = s.makefile("rb")
    with communicate_lang_server(
        write_to, read_from, language_server_client_class=language_server_client_class
    ) as lang_server_client:
        wait_for_test_condition(lambda: len(language_server_instance_final) == 1)
        lang_server_client.language_server_instance = language_server_instance_final[0]
        yield lang_server_client

    if not finish_event.wait(TIMEOUT):
        dump_threads()
        raise AssertionError(
            "Language server thread did not exit in the available timeout."
        )


def _stderr_reader(stderr, buf):
    while True:
        c = stderr.readline()
        if not c:
            break
        buf.append(c)


@contextmanager
def create_language_server_process(log_file, __main__module):
    from robocorp_ls_core.basic import kill_process_and_subprocesses

    from robocorp_ls_core.subprocess_wrapper import subprocess

    language_server_process = subprocess.Popen(
        [
            sys.executable,
            "-u",
            __main__module.__file__,
            "-vv",
            "--log-file=%s" % log_file,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    stderr = language_server_process.stderr
    buf = []
    t = threading.Thread(target=_stderr_reader, args=(stderr, buf))
    t.name = "Stderr reader"
    t.start()

    returncode = language_server_process.poll()
    assert returncode is None
    try:
        yield language_server_process
    finally:
        t.join(1)
        stderr_contents = b"".join(buf).decode("utf-8")
        if stderr_contents:
            sys.stderr.write(f"Found stderr contents: >>\n{stderr_contents}\n<<")
        returncode = language_server_process.poll()
        if returncode is None:
            kill_process_and_subprocesses(language_server_process.pid)


class _OnTimeout(object):
    def __init__(self):
        import pytest_timeout

        self._original_dump_stacks = pytest_timeout.dump_stacks
        pytest_timeout.dump_stacks = self.new_dump_stacks
        self._callbacks = {}  # Note: actually used as an ordered set.

    def new_dump_stacks(self, *args, **kwargs):
        sys.stderr.write("========== CUSTOMIZED TIMEOUT OUTPUT ============\n")
        for c in self._callbacks.copy():
            c()
        sys.stderr.write("======== END CUSTOMIZED TIMEOUT OUTPUT ==========\n")
        return self._original_dump_stacks(*args, **kwargs)

    def add(self, callback):
        self._callbacks[callback] = 1

    def remove(self, callback):
        self._callbacks.pop(callback, None)


_on_timeout = _OnTimeout()


@pytest.fixture
def on_timeout():
    return _on_timeout


@pytest.fixture
def log_file(tmpdir, on_timeout):
    logs_dir = tmpdir.join("logs")
    logs_dir.mkdir()
    filename = str(logs_dir.join("log_test.log"))
    sys.stderr.write("Logging subprocess to: %s" % (filename,))

    def write_on_finish():
        for name in os.listdir(str(logs_dir)):
            sys.stderr.write("\n--- %s contents:\n" % (name,))
            with open(str(logs_dir.join(name)), "r") as stream:
                sys.stderr.write(stream.read())
                sys.stderr.write("\n")

    on_timeout.add(write_on_finish)
    yield filename

    on_timeout.remove(write_on_finish)
    write_on_finish()


@pytest.fixture
def language_server_tcp(
    log_file, main_module, language_server_class, language_server_client_class
):
    """
    Starts a language server in the same process and communicates through tcp.
    """

    with start_language_server_tcp(
        log_file, main_module.main, language_server_class, language_server_client_class
    ) as lang_server_client:
        yield lang_server_client


@pytest.fixture
def language_server_process(log_file, main_module):
    with create_language_server_process(log_file, main_module) as process:
        yield process


@pytest.fixture
def language_server_io(language_server_process):
    """
    Starts a language server in a new process and communicates through stdin/stdout streams.
    """
    write_to = language_server_process.stdin
    read_from = language_server_process.stdout

    with communicate_lang_server(write_to, read_from) as lang_server_client:
        yield lang_server_client


@pytest.fixture(params=["io", "tcp"])
def language_server(request):
    if request.param == "io":
        return request.getfixturevalue("language_server_io")
    else:
        return request.getfixturevalue("language_server_tcp")
