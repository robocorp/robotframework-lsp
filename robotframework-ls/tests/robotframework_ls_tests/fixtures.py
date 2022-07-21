# coding: utf-8
import pytest
import os
import logging
from robocorp_ls_core.unittest_tools.cases_fixture import CasesFixture
from robotframework_ls.constants import NULL
from robocorp_ls_core.watchdog_wrapper import IFSObserver
import sys

__file__ = os.path.abspath(__file__)  # @ReservedAssignment


log = logging.getLogger(__name__)


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

LIBSPEC_3 = """<?xml version="1.0" encoding="UTF-8"?>
<keywordspec name="case3_library" type="library" format="ROBOT" generated="20200316 10:45:35">
<version></version>
<scope>global</scope>
<namedargs>yes</namedargs>
<doc>Documentation for library ``case3_library``.</doc>
<kw name="Case Verify Typing">
<arguments>
<arg>new model:NoneType=10</arg>
</arguments>
<doc></doc>
<tags>
</tags>
</kw>
</keywordspec>
"""


@pytest.fixture
def language_server_client_class():
    from robocorp_ls_core.unittest_tools.language_server_client import (
        LanguageServerClient,
    )

    return LanguageServerClient


@pytest.fixture
def language_server_class():
    from robotframework_ls.robotframework_ls_impl import RobotFrameworkLanguageServer

    return RobotFrameworkLanguageServer


@pytest.fixture
def main_module():
    from robotframework_ls import __main__

    return __main__


def pytest_report_header(config):
    import robot

    print(f"RF Version: {robot.get_version()}")
    print(f"RF Location: {robot.__file__}")


@pytest.fixture(autouse=True, scope="session")
def sync_builtins(tmpdir_factory):
    """
    Pre-generate the builtins.
    """
    from robotframework_ls.impl.libspec_manager import LibspecManager
    import shutil

    user_home = str(tmpdir_factory.mktemp("ls_user_home"))
    os.environ["ROBOTFRAMEWORK_LS_USER_HOME"] = user_home
    os.environ["ROBOTFRAMEWORK_LS_PRE_GENERATE_PYTHONPATH_LIBS"] = "0"
    internal_libspec_dir = LibspecManager.get_internal_builtins_libspec_dir()
    try:
        os.makedirs(internal_libspec_dir)
    except:
        # Ignore exception if it's already created.
        pass

    f = __file__
    original_resources_dir = os.path.join(os.path.dirname(f), "_resources")
    builtin_libs = os.path.join(original_resources_dir, "builtin_libs")
    assert os.path.exists(builtin_libs)

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
def remote_fs_observer(tmpdir, on_timeout):
    def write_on_finish():
        import sys

        dirname = os.path.dirname(log_file)
        for f in os.listdir(dirname):
            if f.startswith(
                "robotframework_api_tests_api_remote_fs_observer"
            ) and f.endswith(".log"):
                full = os.path.join(dirname, f)
                sys.stderr.write("\n--- %s contents:\n" % (full,))
                with open(full, "r") as stream:
                    sys.stderr.write(stream.read())

    on_timeout.add(write_on_finish)

    from robocorp_ls_core.watchdog_wrapper import create_remote_observer

    remote_fsobserver = create_remote_observer(
        "watchdog", (".py", ".libspec", "robot", ".resource")
    )
    log_file = str(tmpdir.join("robotframework_api_tests_api_remote_fs_observer.log"))
    verbose = 0
    remote_fsobserver.start_server(log_file=log_file, verbose=verbose)
    yield remote_fsobserver

    remote_fsobserver.dispose()
    on_timeout.remove(write_on_finish)
    # write_on_finish() -- usually the remote fs observer isn't core to tests, so, don't print by default.


@pytest.fixture
def libspec_manager(tmpdir, remote_fs_observer):
    from robotframework_ls.impl import workspace_symbols as workspace_symbols_module

    workspace_symbols_module.WORKSPACE_SYMBOLS_TIMEOUT = 5

    from robotframework_ls.impl.libspec_manager import LibspecManager

    libspec_manager = LibspecManager(
        user_libspec_dir=str(tmpdir.join("user_libspec")),
        cache_libspec_dir=str(tmpdir.join("cache_libspec")),
        observer=remote_fs_observer,
        dir_cache_dir=str(tmpdir.join(".cache")),
    )
    yield libspec_manager
    libspec_manager.dispose()


def initialize_robotframework_server_api(libspec_manager=NULL):
    from robotframework_ls.server_api.server import RobotFrameworkServerApi
    from io import BytesIO

    read_from = BytesIO()
    write_to = BytesIO()
    robot_framework_server_api = RobotFrameworkServerApi(
        read_from, write_to, libspec_manager=libspec_manager
    )
    robot_framework_server_api.m_initialize()
    return robot_framework_server_api


@pytest.fixture(scope="session")
def cases(tmpdir_factory) -> CasesFixture:
    basename = "res áéíóú"
    copy_to = str(tmpdir_factory.mktemp(basename))

    f = __file__
    original_resources_dir = os.path.join(os.path.dirname(f), "_resources")
    assert os.path.exists(original_resources_dir)

    return CasesFixture(copy_to, original_resources_dir)


class _WorkspaceFixture(object):
    def __init__(self, cases, fs_observer: IFSObserver):
        self._cases = cases
        self._ws = None
        self._fs_observer = fs_observer

    @property
    def ws(self):
        if self._ws is None:
            raise AssertionError(
                "set_root must be called prior to using the workspace."
            )
        return self._ws

    def set_root(self, relative_path, **kwargs):
        path = self._cases.get_path(relative_path)
        self.set_absolute_path_root(path, **kwargs)

    def set_absolute_path_root(self, path, **kwargs):
        from robocorp_ls_core import uris
        from robotframework_ls.impl.robot_workspace import RobotWorkspace

        self._ws = RobotWorkspace(uris.from_fs_path(path), self._fs_observer, **kwargs)

    def get_doc_uri(self, root_relative_path):
        from robocorp_ls_core import uris

        path = os.path.join(self._ws.root_path, root_relative_path)
        uri = uris.from_fs_path(path)
        return uri

    def get_doc(self, root_relative_path, accept_from_file=True):
        return self.ws.get_document(
            self.get_doc_uri(root_relative_path), accept_from_file=accept_from_file
        )

    def put_doc(self, root_relative_path, text=""):
        from robocorp_ls_core.lsp import TextDocumentItem

        return self.ws.put_document(
            TextDocumentItem(uri=self.get_doc_uri(root_relative_path), text=text)
        )


@pytest.fixture
def workspace(cases, remote_fs_observer):
    return _WorkspaceFixture(cases, remote_fs_observer)


@pytest.fixture
def workspace_dir(tmpdir):
    parent = str(tmpdir)
    basename = "ws áéíóú"
    return os.path.join(parent, basename)


def sort_diagnostics(diagnostics):
    def key(diag_dict):
        return (
            diag_dict["source"],
            diag_dict["range"]["start"]["line"],
            diag_dict.get("code", 0),
            diag_dict["severity"],
            diag_dict["message"],
        )

    return sorted(diagnostics, key=key)


def check_code_lens_data_regression(data_regression, found, basename=None):
    import copy

    # For checking the test we need to make the uri/path the same among runs.
    found = copy.deepcopy(found)  # we don't want to change the initial data
    for c in found:
        command = c["command"]
        if command:
            arguments = command["arguments"]
            if arguments:
                arg0 = arguments[0]
                uri = arg0.get("uri")
                if uri:
                    arg0["uri"] = uri.split("/")[-1]

                path = arg0.get("path")
                if path:
                    arg0["path"] = os.path.basename(path)

        data = c.get("data")
        if data:
            uri = data.get("uri")
            if uri:
                data["uri"] = uri.split("/")[-1]
    data_regression.check(found, basename=basename)


class RemoteLibraryExample(object):
    def validate_string(self, string):
        return True

    def verify_that_remote_is_running(self):
        return True


@pytest.fixture
def remote_library(server_port):
    if sys.version_info[0:2] >= (3, 10):
        # Hack to get robotremoteserver to work in Python 3.10!
        from collections.abc import Mapping
        import collections

        collections.Mapping = Mapping

    from robotremoteserver import RobotRemoteServer
    import threading

    server = RobotRemoteServer(
        RemoteLibraryExample(),
        port=server_port,
        serve=False,
    )
    server.activate()
    server_thread = threading.Thread(target=server.serve, args=(False,))
    server_thread.start()
    yield server.server_port
    server.stop()
    server_thread.join()
