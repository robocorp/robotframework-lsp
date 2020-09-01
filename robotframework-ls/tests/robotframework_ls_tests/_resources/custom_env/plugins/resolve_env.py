from typing import Optional

from robocorp_ls_core.pluginmanager import PluginManager
from robotframework_ls.ep_resolve_interpreter import (
    EPResolveInterpreter,
    IInterpreterInfo,
    DefaultInterpreterInfo,
)
from robocorp_ls_core import uris
from pathlib import Path
import sys
import os


class ResolveInterpreterInTests(object):
    def get_interpreter_info_for_doc_uri(self, doc_uri) -> Optional[IInterpreterInfo]:
        as_path = Path(uris.to_fs_path(doc_uri))

        environ = dict(os.environ)

        if as_path.parent.name == "env1":
            return DefaultInterpreterInfo(
                "env1", sys.executable, environ, [str(as_path.parent / "lib1")]
            )

        elif as_path.parent.name == "env2":
            return DefaultInterpreterInfo(
                "env2", sys.executable, environ, [str(as_path.parent / "lib2")]
            )

        return None

    def __typecheckself__(self) -> None:
        from robocorp_ls_core.protocols import check_implements

        _: EPResolveInterpreter = check_implements(self)


def register_plugins(pm: PluginManager):
    pm.register(EPResolveInterpreter, ResolveInterpreterInTests)
