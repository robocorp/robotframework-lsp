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
    from robotframework_ls_tests.conftest import _communicate_lang_server
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
