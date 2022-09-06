import pytest
from robocorp_ls_core.constants import NULL
import os
from robotframework_ls.impl.robot_version import get_robot_major_version


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


_BASIC_TEXT = """
*** Tasks ***
My first task
    Log     Something
    
My second task
    Log     Something
"""


def _build_model_and_check(rf_server_api, uri, data_regression, basename=None):
    build_model_partial = rf_server_api.m_flow_explorer_model(uri)
    result = build_model_partial(monitor=NULL)
    model = result["result"]
    assert model
    # Change model a bit so that it's the same among runs
    model["source"] = os.path.basename(model["source"])
    data_regression.check(model, basename=basename)

    # Uncomment to print model.
    # import json
    #
    # print(json.dumps(model))


def test_flow_explorer_generate_model_basic(rf_server_api, tmpdir, data_regression):
    from robocorp_ls_core import uris

    my = tmpdir.join("my.robot")
    my.write_text(_BASIC_TEXT, "utf-8")
    uri = uris.from_fs_path(str(my))

    _build_model_and_check(rf_server_api, uri, data_regression)


def test_flow_explorer_generate_model_in_memory(rf_server_api, data_regression):
    from robocorp_ls_core.lsp import TextDocumentItem

    uri = "my.robot"
    ws = rf_server_api.workspace
    ws.put_document(TextDocumentItem(uri, text=_BASIC_TEXT))

    _build_model_and_check(
        rf_server_api,
        uri,
        data_regression,
        basename="test_flow_explorer_generate_model_basic",
    )


def test_flow_explorer_generate_model_multi_level(rf_server_api, data_regression):
    from robocorp_ls_core.lsp import TextDocumentItem

    contents = """
*** Tasks ***
My first task
    Call 1

*** Keywords ***    
Call 1
    Call 2
    
Call 2
    Log     Something
"""
    uri = "my.robot"
    ws = rf_server_api.workspace
    ws.put_document(TextDocumentItem(uri, text=contents))

    _build_model_and_check(rf_server_api, uri, data_regression)


def test_flow_explorer_generate_model_arguments(rf_server_api, data_regression):
    from robocorp_ls_core.lsp import TextDocumentItem

    contents = """
*** Tasks ***
My first task
    Call 1    Arg1    Arg2

*** Keywords ***    
Call 1
    [Arguments]    ${arg1}    ${arg2}
    Call 2
"""
    uri = "my.robot"
    ws = rf_server_api.workspace
    ws.put_document(TextDocumentItem(uri, text=contents))

    _build_model_and_check(rf_server_api, uri, data_regression)


@pytest.mark.skipif(get_robot_major_version() < 4, reason="IF not available in RF 3.")
def test_flow_explorer_generate_model_if(rf_server_api, data_regression):
    from robocorp_ls_core.lsp import TextDocumentItem

    contents = """
*** Tasks ***
Main Task
  IF  ${TRUE} AND ${False}
  Main Implemented Keyword
  ELSE
  Comment  Some comment
  END

*** Keywords ***
Main Implemented Keyword
    Another keyword
    
Another keyword
  Comment  Comment in keyword
"""
    uri = "my.robot"
    ws = rf_server_api.workspace
    ws.put_document(TextDocumentItem(uri, text=contents))

    _build_model_and_check(rf_server_api, uri, data_regression)
