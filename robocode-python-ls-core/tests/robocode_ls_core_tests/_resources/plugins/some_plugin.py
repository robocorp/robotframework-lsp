from robocode_ls_core.pluginmanager import PluginManager
from robocode_ls_core_tests.test_pluginmanager import EPFoo


class FooExt(object):
    def Foo(self):
        return "from_plugin"

    def __typecheckself__(self) -> None:
        from robocode_ls_core.protocols import check_implements

        _: EPFoo = check_implements(self)


def register_plugins(pm: PluginManager):
    pm.register(EPFoo, FooExt)
