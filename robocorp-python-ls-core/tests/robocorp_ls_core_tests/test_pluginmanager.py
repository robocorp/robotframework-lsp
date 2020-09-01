# Original work Copyright 2018 Brainwy Software Ltda (Dual Licensed: LGPL / Apache 2.0)
# From https://github.com/fabioz/pyvmmonitor-core
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Robocorp Technologies Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest
from robocorp_ls_core.pluginmanager import PluginManager, InstanceAlreadyRegisteredError
from robocorp_ls_core.protocols import Protocol


class EPFoo(Protocol):
    def __init__(self):
        self.foo = False

    def Foo(self):
        pass


class EPBar(object):
    def __init__(self):
        pass

    def Bar(self):
        pass


class FooImpl(EPFoo):
    def __init__(self):
        pass

    def Foo(self):
        self.foo = True


class AnotherFooImpl(EPFoo):
    pass


def test_plugins():

    from robocorp_ls_core.pluginmanager import NotRegisteredError

    pm = PluginManager()
    pm.register(EPFoo, FooImpl, keep_instance=True)

    with pytest.raises(InstanceAlreadyRegisteredError):
        pm.register(EPFoo, AnotherFooImpl, keep_instance=True)

    foo = pm.get_instance(EPFoo)
    assert pm.get_instance(EPFoo) is foo

    assert pm[EPFoo] is foo
    assert pm["EPFoo"] is foo

    # It's only registered in a way where the instance is kept
    assert not pm.get_implementations(EPFoo)

    assert not pm.get_implementations(EPBar)
    with pytest.raises(NotRegisteredError):
        pm.get_instance(EPBar)

    pm.register(EPFoo, AnotherFooImpl, context="context2", keep_instance=True)

    assert len(list(pm.iter_existing_instances(EPFoo))) == 1
    assert isinstance(pm.get_instance(EPFoo, context="context2"), AnotherFooImpl)

    assert len(list(pm.iter_existing_instances(EPFoo))) == 2
    assert set(pm.iter_existing_instances(EPFoo)) == set(
        [pm.get_instance(EPFoo, context="context2"), pm.get_instance(EPFoo)]
    )

    # Request using a string.
    assert len(list(pm.iter_existing_instances("EPFoo"))) == 2
    assert set(pm.iter_existing_instances("EPFoo")) == set(
        [pm.get_instance(EPFoo, context="context2"), pm.get_instance("EPFoo")]
    )


def test_load_plugins():
    from pathlib import Path

    pm = PluginManager()
    p = Path(__file__).parent / "_resources" / "plugins"
    assert p.exists()
    assert pm.load_plugins_from(p) == 1
    for impl in pm.get_implementations(EPFoo):
        assert impl.Foo() == "from_plugin"


def test_inject():
    from robocorp_ls_core.pluginmanager import inject

    pm = PluginManager()
    pm.register(EPFoo, FooImpl, keep_instance=True)

    @inject(foo=EPFoo)
    def m1(foo, pm):
        return foo

    assert m1(pm=pm) == pm.get_instance(EPFoo)


def test_inject_class():
    from robocorp_ls_core.pluginmanager import inject

    pm = PluginManager()
    pm.register(EPFoo, FooImpl, keep_instance=True)
    pm.register(EPBar, FooImpl, keep_instance=False)
    pm.register(EPBar, AnotherFooImpl, keep_instance=False)

    @inject(foo=EPFoo, foo2=[EPBar])
    def m1(foo, foo2, pm):
        return foo, foo2

    assert m1(pm=pm)[0] == pm.get_instance(EPFoo)
    assert len(m1(pm=pm)[1]) == 2
