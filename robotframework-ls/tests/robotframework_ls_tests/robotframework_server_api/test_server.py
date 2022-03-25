import pytest
import os.path
from robocorp_ls_core.protocols import IRobotFrameworkApiClient
from robotframework_ls_tests.fixtures import initialize_robotframework_server_api

__file__ = os.path.abspath(__file__)
if __file__.endswith((".pyc", ".pyo")):
    __file__ = __file__[:-1]


@pytest.fixture
def server_process(tmpdir, on_timeout, remote_fs_observer):
    from robocorp_ls_core.basic import kill_process_and_subprocesses
    from robotframework_ls.server_api.server__main__ import start_server_process

    log_file = str(tmpdir.join("robotframework_api_tests.log"))

    import robot

    env = {
        "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(robot.__file__)))
    }

    language_server_api_process = start_server_process(
        args=[
            "-vv",
            "--log-file=%s" % log_file,
            f"--remote-fs-observer-port={remote_fs_observer.port}",
        ],
        env=env,
    )
    returncode = language_server_api_process.poll()
    assert returncode is None

    def write_on_finish():
        import sys

        dirname = os.path.dirname(log_file)
        for f in os.listdir(dirname):
            if f.startswith("robotframework_api_tests") and f.endswith(".log"):
                full = os.path.join(dirname, f)
                sys.stderr.write("\n--- %s contents:\n" % (full,))
                with open(full, "r") as stream:
                    sys.stderr.write(stream.read())

    on_timeout.add(write_on_finish)

    yield language_server_api_process

    on_timeout.remove(write_on_finish)

    returncode = language_server_api_process.poll()
    if returncode is None:
        kill_process_and_subprocesses(language_server_api_process.pid)

    write_on_finish()


@pytest.fixture
def server_api_process_io(server_process):
    """
    Starts a language server in a new process and communicates through stdin/stdout streams.
    """
    from robotframework_ls.server_api.client import RobotFrameworkApiClient
    from robocorp_ls_core.unittest_tools.fixtures import communicate_lang_server

    write_to = server_process.stdin
    read_from = server_process.stdout

    with communicate_lang_server(
        write_to,
        read_from,
        language_server_client_class=RobotFrameworkApiClient,
        kwargs={"server_process": server_process},
    ) as lang_server_client:
        yield lang_server_client


def test_server(server_api_process_io: IRobotFrameworkApiClient, data_regression):
    from robotframework_ls_tests.fixtures import sort_diagnostics

    server_api_process_io.initialize(process_id=os.getpid())
    server_api_process_io.settings({"settings": {"robot.lint.robocop.enabled": True}})

    assert server_api_process_io.get_version() >= "3.2"

    server_api_process_io.open("untitled.resource", 1, "*** foo bar ***")

    diag = server_api_process_io.lint("untitled.resource")["result"]
    data_regression.check(sort_diagnostics(diag), basename="errors")


def test_server_cancel(
    server_api_process_io: IRobotFrameworkApiClient, data_regression
):
    from robocorp_ls_core.jsonrpc.endpoint import FORCE_NON_THREADED_VERSION

    if FORCE_NON_THREADED_VERSION:
        pytest.skip(
            "Can only test server cancelling when the threaded version is enabled."
        )
    import time

    server_api_process_io.initialize(process_id=os.getpid())

    big_contents = "*** foo bar ***\n" * 100000

    server_api_process_io.open("untitled", 1, big_contents)
    message_matcher = server_api_process_io.request_lint("untitled")
    assert message_matcher
    time.sleep(0.5)  # Wait a bit to make sure it's inside the lint.
    server_api_process_io.request_cancel(message_matcher.message_id)
    message_matcher.event.wait(10)
    assert message_matcher.msg == {
        "jsonrpc": "2.0",
        "id": message_matcher.message_id,
        "error": {"code": -32800, "message": "Lint cancelled (inside lint)"},
    }


def _build_launch_env():
    import sys

    environ = os.environ.copy()
    cwd = os.path.abspath(os.path.dirname(__file__))
    assert os.path.isdir(cwd)

    environ["PYTHONPATH"] = (
        cwd
        + os.pathsep
        + environ.get("PYTHONPATH", "")
        + os.pathsep
        + os.pathsep.join(sys.path)
    )
    return cwd, environ


def _check_in_separate_process(method_name, module_name="test_server", update_env={}):
    from robocorp_ls_core.subprocess_wrapper import subprocess
    import sys

    cwd, environ = _build_launch_env()
    environ.update(update_env)

    subprocess.check_call(
        [
            sys.executable,
            "-c",
            "import %(module_name)s;%(module_name)s.%(method_name)s()"
            % dict(method_name=method_name, module_name=module_name),
        ],
        env=environ,
        cwd=cwd,
    )


def test_check_version():
    api = initialize_robotframework_server_api()
    # In tests we always have at least 3.2.
    assert api._compute_min_version_error((3, 2)) is None

    assert api._compute_min_version_error((22, 1)).startswith(
        "Expected Robot Framework version: 22.1. Found: "
    )

    api._version = "3.1"
    assert api._compute_min_version_error((3, 2)).startswith(
        "Expected Robot Framework version: 3.2. Found: 3.1"
    )

    api._version = "3.2"
    assert api._compute_min_version_error((3, 2)) is None


def check_no_robotframework():
    from robocorp_ls_core.basic import before
    import sys

    import builtins

    def fail_robot_import(name, *args, **kwargs):
        if name == "robot" or name.startswith("robot."):
            raise ImportError()

    with before(builtins, "__import__", fail_robot_import):
        api = initialize_robotframework_server_api()
        assert "robot" not in sys.modules
        msg = (
            'Error in "import robot".\n'
            f"It seems that Robot Framework is not installed in {sys.executable}.\n"
            "Please install it in your environment and restart the Robot Framework Language Server\n"
            'or set: "robot.language-server.python" or "robot.python.executable"\n'
            "to point to a python installation that has Robot Framework installed.\n"
            "Hint: with pip it can be installed with:\n"
            f"{sys.executable} -m pip install robotframework\n"
        )

        assert api.m_version() == msg
        result = api.m_lint("something foo bar")
        assert result == [
            {
                "range": {
                    "start": {"character": 0, "line": 0},
                    "end": {"character": 0, "line": 1},
                },
                "message": (msg),
                "source": "robotframework",
                "severity": 1,
            }
        ]


def check_robotframework_load():
    import sys

    api = initialize_robotframework_server_api()
    # Just initializing should not try to load robotframework
    assert "robot" not in sys.modules
    assert api.m_version() is not None
    assert "robot" in sys.modules


def test_server_requisites():
    _check_in_separate_process("check_no_robotframework")
    _check_in_separate_process("check_robotframework_load")


def test_server_complete_all():
    from robocorp_ls_core.jsonrpc.monitor import Monitor

    api = initialize_robotframework_server_api()

    try:
        uri = "<untitled>"
        api.m_text_document__did_open(textDocument={"uri": uri})
        api.m_text_document__did_change(
            textDocument={"uri": uri},
            contentChanges=[
                {
                    "text": """
*** Variables ***
&{Person}         Address=&{home_address}
&{home_address}   City=Somewhere   Zip Code=12345

*** Test Cases ***
Dictionary Variable
    Log to Console    ${Person}[]"""
                }
            ],
        )
        doc = api.workspace.get_document(uri, accept_from_file=False)
        line, col = doc.get_last_line_col()
        monitor = Monitor()
        completions = api.m_complete_all(uri, line, col - 1)(monitor=monitor)
    finally:
        api.m_exit()
        api.m_shutdown()
    assert set(x["label"] for x in completions) == {"Address"}
