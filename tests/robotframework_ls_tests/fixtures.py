import threading
import pytest
from contextlib import contextmanager
import os
import logging
import sys
from robotframework_ls.options import USE_TIMEOUTS, NO_TIMEOUT

__file__ = os.path.abspath(__file__)  # @ReservedAssignment


log = logging.getLogger(__name__)

TIMEOUT = int(os.getenv("PYTEST_TIMEOUT", 7))
if not USE_TIMEOUTS:
    TIMEOUT = NO_TIMEOUT  # i.e.: None

LIBSPEC_1 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case1_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case1_library``.</doc>
<kw name="new Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="New Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

LIBSPEC_2 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case2_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case2_library``.</doc>
<kw name="Case 2 Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="Case 2 Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""

LIBSPEC_2_A = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case2_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case2_library``.</doc>
<kw name="Case 2 A Verify Another Model">
<arguments>
<arg>new model=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
<kw name="Case 2 A Verify Model">
<arguments>
<arg>new model</arg>
</arguments>
<doc>:type new_model: int</doc>
<tags>
</tags>
</kw>
</keywordspec>
"""


def wait_for_condition(condition, msg=None, timeout=TIMEOUT, sleep=1 / 20.0):
    from robotframework_ls._utils import wait_for_condition as w

    return w(condition, msg=msg, timeout=timeout, sleep=sleep)


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
    language_server_instance_final = []

    def after_bind(server):
        address = server.socket.getsockname()
        config.address = address
        start_event.set()

    def start_language_server():
        def language_server_class(*args, **kwargs):
            from robotframework_ls.robotframework_ls_impl import (
                RobotFrameworkLanguageServer,
            )

            language_server_instance = RobotFrameworkLanguageServer(*args, **kwargs)
            language_server_instance_final.append(language_server_instance)
            return language_server_instance

        main(
            [
                "--tcp",
                "--host=127.0.0.1",
                "--port=0",
                "-vv",
                "--log-file=%s" % log_file,
            ],
            after_bind=after_bind,
            language_server_class=language_server_class,
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
        wait_for_condition(lambda: len(language_server_instance_final) == 1)
        lang_server_client.language_server_instance = language_server_instance_final[0]
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

    from robotframework_ls.robotframework_log import configure_logger

    configure_logger("test", 2)


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
    returncode = language_server_process.poll()
    assert returncode is None
    yield language_server_process
    returncode = language_server_process.poll()
    if returncode is None:
        kill_process_and_subprocesses(language_server_process.pid)


@pytest.fixture(autouse=True, scope="session")
def sync_builtins(tmpdir_factory, cases):
    """
    Pre-generate the builtins.
    """
    from robotframework_ls.impl.libspec_manager import LibspecManager
    import shutil

    user_home = str(tmpdir_factory.mktemp("ls_user_home"))
    os.environ["ROBOTFRAMEWORK_LS_USER_HOME"] = user_home
    internal_libspec_dir = LibspecManager.get_internal_builtins_libspec_dir()
    try:
        os.makedirs(internal_libspec_dir)
    except:
        # Ignore exception if it's already created.
        pass

    builtin_libs = cases.get_path("builtin_libs")

    # Uncomment the line to regenerate the libspec files for the builtin libraries.
    # LibspecManager(builtin_libspec_dir=builtin_libs)

    # Note: use private copy instead of re-creating because it's one of the
    # slowest things when starting test cases.
    # Locally it's the difference from the test suite taking 15 or 25 seconds
    # (with tests with 12 cpus in parallel).

    for name in os.listdir(builtin_libs):
        shutil.copyfile(
            os.path.join(builtin_libs, name), os.path.join(internal_libspec_dir, name)
        )


@pytest.fixture
def libspec_manager(tmpdir):
    from robotframework_ls.impl.libspec_manager import LibspecManager

    libspec_manager = LibspecManager(user_libspec_dir=str(tmpdir.join("user_libspec")))
    yield libspec_manager
    libspec_manager.dispose()


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


class _CasesFixture(object):
    def __init__(self):
        self.resources_dir = os.path.join(os.path.dirname(__file__), "_resources")
        assert os.path.exists(self.resources_dir)

    def get_path(self, resources_relative_path, must_exist=True):
        path = os.path.join(self.resources_dir, resources_relative_path)
        if must_exist:
            assert os.path.exists(path), "%s does not exist." % (path,)
        return path

    def copy_to(self, case, dest_dir):
        import shutil

        shutil.copytree(self.get_path(case, must_exist=True), dest_dir)


@pytest.fixture(scope="session")
def cases():
    return _CasesFixture()


class _WorkspaceFixture(object):
    def __init__(self, cases):
        self._cases = cases
        self._ws = None

    @property
    def ws(self):
        if self._ws is None:
            raise AssertionError(
                "set_root must be called prior to using the workspace."
            )
        return self._ws

    def set_root(self, relative_path, **kwargs):
        from robotframework_ls import uris
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        path = self._cases.get_path(relative_path)
        self._ws = RobotWorkspace(uris.from_fs_path(path), **kwargs)

    def get_doc(self, root_relative_path, create=True):
        from robotframework_ls import uris

        path = os.path.join(self._ws.root_path, root_relative_path)
        uri = uris.from_fs_path(path)
        return self.ws.get_document(uri, create=create)


@pytest.fixture
def workspace(cases):
    return _WorkspaceFixture(cases)
