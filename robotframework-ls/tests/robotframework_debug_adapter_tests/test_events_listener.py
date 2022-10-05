from robotframework_debug_adapter_tests.fixtures import _DebuggerAPI


def test_events_listener_basic(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        StartTestEvent,
        EndTestEvent,
        EndSuiteEvent,
        StartSuiteEvent,
        TerminatedEvent,
    )

    target = debugger_api.get_dap_case_file("case_evaluate.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    start_suite_event = debugger_api.read(StartSuiteEvent).body
    assert start_suite_event.tests == ["Can use resource keywords"]
    assert debugger_api.read(StartTestEvent)
    assert debugger_api.read(EndTestEvent)
    assert debugger_api.read(EndSuiteEvent)
    debugger_api.read(TerminatedEvent)


def test_events_listener_failure(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
        StartTestEvent,
        EndTestEvent,
        EndSuiteEvent,
        StartSuiteEvent,
        TerminatedEvent,
    )
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import LogMessageEvent
    from robotframework_ls.impl.robot_version import get_robot_major_version

    target = debugger_api.get_dap_case_file("case_failure.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    assert debugger_api.read(StartSuiteEvent)
    start_test_event = debugger_api.read(StartTestEvent)
    assert start_test_event.body.source.endswith("case_failure.robot")

    log_message_body = debugger_api.read(LogMessageEvent).body
    assert "No keyword with name" in log_message_body.message
    assert log_message_body.level == "FAIL"
    assert log_message_body.testName == "Check failure"

    if get_robot_major_version() >= 4:
        # source is not available on RF 3.
        assert log_message_body.source.endswith("case_failure.robot")
        assert log_message_body.lineno == 4

    end_test_body = debugger_api.read(EndTestEvent).body
    assert end_test_body.status == "FAIL"
    assert (
        "No keyword with name 'This keyword does not exist' found."
        in end_test_body.message
    )

    assert "Traceback:" in end_test_body.message
    assert debugger_api.read(EndSuiteEvent)

    debugger_api.read(TerminatedEvent)


def test_events_listener_output(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    import robot
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import LogMessageEvent
    from robotframework_ls.impl.robot_version import get_robot_major_version

    target = debugger_api.get_dap_case_file("case_log_no_console.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    assert debugger_api.read(StartSuiteEvent)
    assert debugger_api.read(StartTestEvent)

    log_message_body = debugger_api.read(LogMessageEvent).body
    assert log_message_body.message.strip() == "LogNoConsole"
    assert log_message_body.level == "INFO"
    assert log_message_body.testName == "Check log"

    # Source not available in RF 3.
    if get_robot_major_version() >= 4:
        assert log_message_body.source.endswith("case_log_no_console.robot")
        assert log_message_body.lineno == 4

    end_test_body = debugger_api.read(EndTestEvent).body
    assert end_test_body.status == "PASS"
    assert not end_test_body.failed_keywords

    assert debugger_api.read(EndSuiteEvent)

    debugger_api.read(TerminatedEvent)


def test_events_listener_output_error(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import LogMessageEvent

    target = debugger_api.get_dap_case_file("case_log_error.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    assert debugger_api.read(StartSuiteEvent)
    assert debugger_api.read(StartTestEvent)

    log_message_body = debugger_api.read(LogMessageEvent).body
    assert "log_an_error" in log_message_body.message

    end_test_body = debugger_api.read(EndTestEvent).body
    assert end_test_body.status == "PASS"
    assert not end_test_body.failed_keywords

    assert debugger_api.read(EndSuiteEvent)

    debugger_api.read(TerminatedEvent)


def test_events_listener_output_import_error(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import LogMessageEvent

    target = debugger_api.get_dap_case_file("case_import_failure.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    debugger_api.read(LogMessageEvent)

    assert debugger_api.read(StartSuiteEvent)
    assert debugger_api.read(StartTestEvent)

    end_test_body = debugger_api.read(EndTestEvent).body
    assert end_test_body.status == "PASS"
    assert not end_test_body.failed_keywords

    assert debugger_api.read(EndSuiteEvent)

    debugger_api.read(TerminatedEvent)


def test_events_listener_ignore(debugger_api: _DebuggerAPI):
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import StartTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndTestEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import EndSuiteEvent
    from robocorp_ls_core.debug_adapter_core.dap.dap_schema import TerminatedEvent

    target = debugger_api.get_dap_case_file("case_failure_handled.robot")
    debugger_api.target = target

    debugger_api.launch(
        target,
        debug=False,
        args=[
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV2",
            "--listener=robotframework_debug_adapter.events_listener.EventsListenerV3",
        ],
    )

    debugger_api.configuration_done()

    assert debugger_api.read(StartSuiteEvent)
    assert debugger_api.read(StartTestEvent)
    end_test_body = debugger_api.read(EndTestEvent).body
    assert end_test_body.status == "PASS"
    assert not end_test_body.failed_keywords

    assert debugger_api.read(EndSuiteEvent)

    debugger_api.read(TerminatedEvent)
