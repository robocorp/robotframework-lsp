def test_command_dispatch():
    from robocorp_ls_core.command_dispatcher import (
        _CommandDispatcher,
        _SubCommandDispatcher,
    )

    command_dispatcher = _CommandDispatcher()

    class BaseCls(object):
        def __init__(self):
            self._sub = SubCls()

        @command_dispatcher("action1")
        def call1(self):
            return "call1"

    sub_dispatcher = _SubCommandDispatcher("_sub")

    class SubCls(object):
        @command_dispatcher("action2")
        def sub1(self):
            return "sub1"

    c = BaseCls()
    command_dispatcher.register_sub_command_dispatcher(sub_dispatcher)

    assert command_dispatcher.dispatch(c, "action1", ()) == "call1"
    assert command_dispatcher.dispatch(c, "action2", ()) == "sub1"
    action_result = command_dispatcher.dispatch(c, "action_not_there", ())
    assert action_result["success"] == False
