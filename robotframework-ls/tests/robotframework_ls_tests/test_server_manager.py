from typing import Optional

import pytest

from robocorp_ls_core.basic import implements
from robotframework_ls.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
    DefaultInterpreterInfo,
)


class ResolveInterpreterInTest(object):
    @implements(EPResolveInterpreter.get_interpreter_info_for_doc_uri)
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        if doc_uri == "doc_uri_1":
            return DefaultInterpreterInfo("doc1", "python_exe_doc1", None, None)
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


@pytest.fixture
def server_manager(pm, config):
    from robotframework_ls.server_manager import ServerManager

    return ServerManager(pm, config=config)


def test_server_manager(pm, server_manager):
    import sys

    assert not server_manager._id_to_apis

    api_source_format = server_manager.get_source_format_api()
    api_default = server_manager.get_regular_api("")
    assert api_source_format is api_default

    assert len(server_manager._id_to_apis) == 1
    for api in server_manager._iter_all_apis():
        assert api._server_process is None, "API should be lazy-loaded."

    api_doc_uri1 = server_manager.get_regular_api("doc_uri_1")
    assert api_doc_uri1 is not api_source_format
    assert api_default._get_python_executable() == sys.executable
    assert api_doc_uri1._get_python_executable() == "python_exe_doc1"
