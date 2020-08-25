from typing import Optional

from robocode_ls_core.basic import implements
from robocode_ls_core.pluginmanager import PluginManager
from robotframework_ls.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
)


class ResolveInterpreter(object):
    @implements(EPResolveInterpreter.get_interpreter_info_for_doc_uri)
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        return None

    def __typecheckself__(self) -> None:
        from robocode_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


def register_plugins(pm: PluginManager):
    pm.register(EPResolveInterpreter, ResolveInterpreter)
