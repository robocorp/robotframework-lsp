from typing import Optional

import pytest

from robocorp_ls_core.basic import implements
from robotframework_ls.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
    DefaultInterpreterInfo,
)
import sys
from robocorp_ls_core.constants import NULL


class ResolveInterpreterInTest(object):
    @implements(EPResolveInterpreter.get_interpreter_info_for_doc_uri)
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        if doc_uri == "doc_uri_1":
            return DefaultInterpreterInfo("doc1", "python_exe_doc1", None, [])
        return None

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


@pytest.fixture
def config():
    from robotframework_ls.robot_config import RobotConfig

    return RobotConfig()


@pytest.fixture
def pm():
    from robocorp_ls_core.pluginmanager import PluginManager

    p = PluginManager()
    p.register(EPResolveInterpreter, ResolveInterpreterInTest)
    return p


class _DummyLanguageServer(object):
    def __init__(self):
        self._fs_observer = None

    def get_remote_fs_observer_port(self):
        if self._fs_observer is None:
            from robocorp_ls_core import watchdog_wrapper

            self._fs_observer = watchdog_wrapper.create_remote_observer(
                "fsnotify", (".py", ".libspec", "robot", ".resource")
            )
            self._fs_observer.start_server()
        return self._fs_observer.port

    def dispose(self):
        if self._fs_observer is not None:
            self._fs_observer.dispose()
            self._fs_observer = NULL


@pytest.fixture
def dummy_language_server():
    ret = _DummyLanguageServer()
    yield ret
    ret.dispose()


@pytest.fixture
def server_manager(pm, config, dummy_language_server):
    from robotframework_ls.server_manager import ServerManager

    return ServerManager(pm, config=config, language_server=dummy_language_server)


def test_server_manager_basic(pm, server_manager) -> None:
    assert not server_manager._id_to_apis

    api_source_format = server_manager._get_others_api("")
    api_default = server_manager._get_regular_api("")
    assert api_source_format is not api_default

    assert len(server_manager._id_to_apis) == 1
    for api in server_manager._iter_all_apis():
        assert api._server_process is None, "API should be lazy-loaded."

    api_doc_uri1 = server_manager._get_regular_api("doc_uri_1")
    assert api_doc_uri1 is not api_default
    assert api_default._get_python_executable() == sys.executable
    assert api_doc_uri1._get_python_executable() == "python_exe_doc1"

    # At this point it wasn't initialized! It's not valid in this test anyways...
    assert api_doc_uri1.stats is None


class ResolveInterpreterInTestValid(object):
    @implements(EPResolveInterpreter.get_interpreter_info_for_doc_uri)
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        if doc_uri == "doc_uri_1":
            return DefaultInterpreterInfo("doc1", sys.executable, {"var1": "var1"}, [])
        return None

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


def test_server_manager_dont_forward_setting_unless_changed(
    pm, server_manager, workspace, workspace_dir, cases
) -> None:
    from robocorp_ls_core.config import Config

    pm.unregister(EPResolveInterpreter)
    pm.register(EPResolveInterpreter, ResolveInterpreterInTestValid)

    api_doc_uri1 = server_manager._get_regular_api("doc_uri_1")

    # At this point it wasn't initialized!
    assert api_doc_uri1.stats is None

    cases.copy_to("case1", workspace_dir)
    workspace.set_root(workspace_dir)

    config = Config()
    config.update({"var1": "var1"})
    server_manager.set_workspace(workspace.ws)
    server_manager.set_config(config)
    assert api_doc_uri1._server_process is None, "API should be lazy-loaded."

    client = api_doc_uri1.get_robotframework_api_client()
    assert api_doc_uri1._server_process is not None
    assert api_doc_uri1.stats == {
        "initialize": 1,
        "workspace/didChangeConfiguration": 1,
    }

    client.open("uri", 1, "*** Sett")
    client.request_complete_all("uri", 0, 8)
    assert api_doc_uri1.stats == {
        "initialize": 1,
        "workspace/didChangeConfiguration": 1,
        "textDocument/didOpen": 1,
        "completeAll": 1,
    }

    client.request_complete_all("uri", 0, 8)
    assert api_doc_uri1.stats == {
        "initialize": 1,
        "workspace/didChangeConfiguration": 1,
        "textDocument/didOpen": 1,
        "completeAll": 2,
    }

    config = Config()
    config.update({"var2": "var2"})
    server_manager.set_config(config)
    assert api_doc_uri1.stats == {
        "initialize": 1,
        "workspace/didChangeConfiguration": 2,
        "textDocument/didOpen": 1,
        "completeAll": 2,
    }
    client.request_complete_all("uri", 0, 8)
    assert api_doc_uri1.stats == {
        "initialize": 1,
        "workspace/didChangeConfiguration": 2,
        "textDocument/didOpen": 1,
        "completeAll": 3,
    }
