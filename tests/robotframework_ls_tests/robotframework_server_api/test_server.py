import pytest


@pytest.fixture
def server_process(tmpdir):
    import os.path
    from robotframework_ls._utils import kill_process_and_subprocesses
    from robotframework_ls.server_api.server__main__ import start_server_process

    log_file = str(tmpdir.join("robotframework_api_tests.log"))

    language_server_api_process = start_server_process(
        args=["-vv", "--log-file=%s" % log_file]
    )
    assert language_server_api_process.returncode is None
    yield language_server_api_process
    if language_server_api_process.returncode is None:
        kill_process_and_subprocesses(language_server_api_process.pid)

    if os.path.exists(log_file):
        print("--- %s contents:" % (log_file,))
        with open(log_file, "r") as stream:
            print(stream.read())


@pytest.fixture
def server_api_process_io(server_process):
    """
    Starts a language server in a new process and communicates through stdin/stdout streams.
    """
    from robotframework_ls_tests.fixtures import _communicate_lang_server
    from robotframework_ls.server_api.client import RobotFrameworkApiClient

    write_to = server_process.stdin
    read_from = server_process.stdout

    with _communicate_lang_server(
        write_to,
        read_from,
        language_server_client_class=RobotFrameworkApiClient,
        kwargs={"server_process": server_process},
    ) as lang_server_client:
        yield lang_server_client


def test_server(server_api_process_io, data_regression):
    import os

    server_api_process_io.initialize(process_id=os.getpid())
    assert server_api_process_io.get_version() == "3.2"
    data_regression.check(
        server_api_process_io.lint("*** foo bar ***"), basename="errors"
    )


def _build_launch_env():
    import os

    environ = os.environ.copy()
    cwd = os.path.abspath(os.path.dirname(__file__))
    assert os.path.isdir(cwd)

    environ["PYTHONPATH"] = cwd + os.pathsep + environ.get("PYTHONPATH", "")
    return cwd, environ


def _check_in_separate_process(method_name, module_name="test_server", update_env={}):
    import subprocess
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


def _initialize_robotframework_server_api():
    from robotframework_ls.server_api.server import RobotFrameworkServerApi
    from io import BytesIO

    read_from = BytesIO()
    write_to = BytesIO()
    robot_framework_server_api = RobotFrameworkServerApi(read_from, write_to)
    robot_framework_server_api.m_initialize()
    return robot_framework_server_api


def test_check_version():
    api = _initialize_robotframework_server_api()
    # In tests we always have at least 3.2.
    assert api._check_min_version((3, 2))

    assert not api._check_min_version((22, 1))

    api._version = "3.1"
    assert not api._check_min_version((3, 2))

    api._version = "3.2"
    assert api._check_min_version((3, 2))


def check_no_robotframework():
    from robotframework_ls._utils import before
    from robotframework_ls.constants import IS_PY2
    import sys

    if IS_PY2:
        import __builtin__ as builtins
    else:
        import builtins

    def fail_robot_import(name, *args, **kwargs):
        if name == "robot" or name.startswith("robot."):
            raise ImportError()

    with before(builtins, "__import__", fail_robot_import):
        api = _initialize_robotframework_server_api()
        assert "robot" not in sys.modules
        assert api.m_version() == "N/A"
        result = api.m_lint("something foo bar")
        assert result == [
            {
                "range": {
                    "start": {"character": 0, "line": 0},
                    "end": {"character": 0, "line": 1},
                },
                "message": (
                    "robotframework version (N/A) too old for linting.\n"
                    "Please install a newer version and restart the language server."
                ),
                "source": "robotframework",
                "severity": 1,
            }
        ]


def check_robotframework_load():
    import sys

    api = _initialize_robotframework_server_api()
    # Just initializing should not try to load robotframework
    assert "robot" not in sys.modules
    assert api.m_version() is not None
    assert "robot" in sys.modules


def test_server_requisites():
    _check_in_separate_process("check_no_robotframework")
    _check_in_separate_process("check_robotframework_load")
