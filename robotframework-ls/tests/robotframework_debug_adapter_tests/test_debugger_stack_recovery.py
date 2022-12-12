class _SuiteData:
    def __init__(self, name, source):
        self.name = name
        self.source = source


class _TestData:
    def __init__(self, name, source, lineno):
        self.name = name
        self.source = source
        self.lineno = lineno


class _SuiteResult:
    pass


def test_impl_recovery_matches_suite():

    from robotframework_debug_adapter.debugger_impl import _RobotDebuggerImpl

    impl = _RobotDebuggerImpl()
    result = _SuiteResult()

    suite_data = _SuiteData("name", "source")
    impl.start_suite(suite_data, result)

    test_data = _TestData("test", "source", 0)
    impl.start_test(test_data, result)

    assert len(impl._stack_ctx_entries_deque) == 2

    # Unsynchronized end suite (clear until we reach it).
    impl.end_suite(suite_data, result)

    assert len(impl._stack_ctx_entries_deque) == 0


class _Variables:
    def __init__(self):
        self.current = {}


class _Context:
    def __init__(self):
        self.variables = _Variables()


def test_impl_recovery_matches_test():
    from robotframework_debug_adapter.debugger_impl import _RobotDebuggerImpl

    impl = _RobotDebuggerImpl()
    result = _SuiteResult()

    suite_data = _SuiteData("name", "source")
    impl.start_suite(suite_data, result)

    test_data = _TestData("test", "source", 0)
    impl.start_test(test_data, result)

    keyword_data = {
        "lineno": 0,
        "source": "source",
        "kwname": "kwname",
        "args": [],
        "type": "KEYWORD",
    }
    from robot.running.context import EXECUTION_CONTEXTS

    EXECUTION_CONTEXTS._contexts.append(_Context())
    impl.start_keyword_v2("kwname", keyword_data)

    assert len(impl._stack_ctx_entries_deque) == 3

    # Unsynchronized end test (clear until we reach it).
    impl.end_test(test_data, result)
    assert len(impl._stack_ctx_entries_deque) == 1

    impl.end_suite(suite_data, result)
    assert len(impl._stack_ctx_entries_deque) == 0


def test_impl_recovery_does_not_match_test():
    from robotframework_debug_adapter.debugger_impl import _RobotDebuggerImpl

    impl = _RobotDebuggerImpl()
    result = _SuiteResult()

    suite_data = _SuiteData("name", "source")
    impl.start_suite(suite_data, result)

    test_data = _TestData("test", "source", 0)
    impl.start_test(test_data, result)

    keyword_data = {
        "lineno": 0,
        "source": "source",
        "kwname": "kwname",
        "args": [],
        "type": "KEYWORD",
    }
    from robot.running.context import EXECUTION_CONTEXTS

    EXECUTION_CONTEXTS._contexts.append(_Context())
    impl.start_keyword_v2("kwname", keyword_data)

    assert len(impl._stack_ctx_entries_deque) == 3

    # Unsynchronized end test (clear all keywords).
    test_data = _TestData("no-match-test", "source", 0)

    impl.end_test(test_data, result)
    assert len(impl._stack_ctx_entries_deque) == 1
    impl.end_suite(suite_data, result)
    assert len(impl._stack_ctx_entries_deque) == 0


def test_impl_recovery_do_nothing():
    from robotframework_debug_adapter.debugger_impl import _RobotDebuggerImpl

    suite_data = _SuiteData("name", "source")
    impl = _RobotDebuggerImpl()
    result = _SuiteResult()

    impl.end_suite(suite_data, result)
    assert len(impl._stack_ctx_entries_deque) == 0
