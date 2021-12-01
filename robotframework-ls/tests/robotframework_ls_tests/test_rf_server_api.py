import pytest


@pytest.fixture
def rf_server_api(tmpdir):
    from robotframework_ls_tests.fixtures import initialize_robotframework_server_api
    from robotframework_ls.server_api.server import RobotFrameworkServerApi
    from robocorp_ls_core import uris

    api: RobotFrameworkServerApi = initialize_robotframework_server_api(
        libspec_manager=None  # It'll be auto-initialized as needed.
    )
    root_uri = uris.from_fs_path(str(tmpdir))
    api.m_initialize(rootUri=root_uri)
    yield api
    api.m_shutdown()
    api.m_exit()


def test_complete_from_context(rf_server_api, libspec_manager, tmpdir):
    from robotframework_ls.impl.completion_context import CompletionContext
    from robotframework_ls.impl.robot_workspace import RobotDocument
    from robotframework_ls.impl.robot_workspace import RobotWorkspace
    from robocorp_ls_core.watchdog_wrapper import create_observer

    api = rf_server_api

    text = """*** Task ***
Some task
    Log    Something     console=True
    Lo"""

    doc = RobotDocument("", text)

    line, col = doc.get_last_line_col()
    workspace = RobotWorkspace(
        str(tmpdir),
        fs_observer=create_observer("dummy", ()),
        libspec_manager=libspec_manager,
    )
    completion_context = CompletionContext(doc, line, col, workspace=workspace)

    completions = api._complete_from_completion_context(completion_context)
    for completion in completions:
        if completion["label"] == "Log (BuiltIn)":
            break
    else:
        raise AssertionError(
            f'Did not find "Log" entry in completions. Found: {list(x["label"] for x in completions)}'
        )
