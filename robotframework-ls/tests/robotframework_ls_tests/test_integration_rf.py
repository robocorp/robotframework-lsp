"""
This is an integration test. It will check that the language server works with
RobotFramework itself.
"""
from pathlib import Path
import pytest
from robocorp_ls_core.constants import NULL


@pytest.fixture
def rf_root():
    import robot

    init = Path(robot.__file__)
    robot_path = init.parent
    src = robot_path.parent
    root = src.parent

    if not (root / "atest" / "resources").exists():
        pytest.skip("A source distribution of robotframework is needed for this test.")

    return root


@pytest.fixture
def rf_configured_api(rf_root):
    from robotframework_ls_tests.fixtures import initialize_robotframework_server_api
    from robotframework_ls.server_api.server import RobotFrameworkServerApi
    from robocorp_ls_core import uris

    api: RobotFrameworkServerApi = initialize_robotframework_server_api(
        libspec_manager=None  # It'll be auto-initialized as needed.
    )
    root_uri = uris.from_fs_path(str(rf_root))
    api.m_initialize(rootUri=root_uri)
    api.m_workspace__did_change_configuration(
        settings={"robot.pythonpath": [str(rf_root / "atest" / "resources")]}
    )
    yield api
    api.m_shutdown()
    api.m_exit()


def test_robotframework_integrated_go_to_def(rf_configured_api, rf_root):
    from robocorp_ls_core import uris
    from robocorp_ls_core.workspace import Document

    api = rf_configured_api

    doc_uri = uris.from_fs_path(str(rf_root / "atest" / "resources" / "foobar.robot"))
    text = """*** Settings ***
Library           TestCheckerLibrary"""

    api.m_text_document__did_open(textDocument={"uri": doc_uri, "text": text})
    doc = Document("")
    doc.source = text

    line, col = doc.get_last_line_col()
    func = api.m_find_definition(doc_uri, line, col)
    found = func(monitor=NULL)
    assert len(found) == 1
    found[0]["uri"].endswith("TestCheckerLibrary.py")


def test_robotframework_integrated_completions(rf_configured_api, rf_root):
    from robocorp_ls_core import uris
    from robocorp_ls_core.workspace import Document

    api = rf_configured_api

    doc_uri = uris.from_fs_path(
        str(rf_root / "atest" / "robot" / "cli" / "dryrun" / "args.robot")
    )
    text = """*** Settings ***
Suite Setup      Run Tests    --dryrun    cli/dryrun/args.robot
Resource         atest_resource.robot

*** Test Cases ***
Valid positional args
    Check Test Case    ${TESTNAME}

Too few arguments
    Check Test Case    ${TESTNAME}

Too few arguments for UK
    Check Test Case    ${TESTNAME}

Too many arguments
    Check Test Case    ${TESTNAME}

Valid named args
    Check Test Case    ${TESTNAME}

Invalid named args
    Check Test Case    ${TESTNAME}
    Ch"""

    api.m_text_document__did_open(textDocument={"uri": doc_uri, "text": text})
    api.workspace.wait_for_check_done(10)
    doc = Document("")
    doc.source = text

    PRINT_TIMES = False
    if PRINT_TIMES:
        import time

        curtime = time.time()

    for i in range(5):
        line, col = doc.get_last_line_col()
        func = api.m_complete_all(doc_uri, line, col)
        assert len(func(monitor=NULL)) > 10
        if PRINT_TIMES:
            print("Total %s: %.2fs" % (i, time.time() - curtime))
            curtime = time.time()
