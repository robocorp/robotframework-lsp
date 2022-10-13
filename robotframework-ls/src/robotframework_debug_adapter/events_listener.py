from typing import Any, Dict, List, Deque, Optional
from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
    StartSuiteEvent,
    StartSuiteEventBody,
    StartTestEvent,
    StartTestEventBody,
    EndSuiteEvent,
    EndSuiteEventBody,
    EndTestEvent,
    EndTestEventBody,
)
from collections import namedtuple
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core import uris
import sys
from robotframework_ls.impl.robot_version import get_robot_major_version

log = get_logger(__name__)


def send_event(event):
    from robotframework_debug_adapter.global_vars import get_global_robot_target_comm

    robot_target_comm = get_global_robot_target_comm()
    if robot_target_comm is not None:
        robot_target_comm.write_message(event)


_SourceInfo = namedtuple("_SourceInfo", "source, lineno, test_name, keyword_name, args")


class _EventsState:
    def __init__(self):
        from collections import deque
        from robotframework_debug_adapter._ignore_failures_in_stack import (
            IgnoreFailuresInStack,
        )

        self._failure_messages: List[str] = []

        self._last_failure_message = ""
        self._last_failure_message_full_stacktrace = ""
        self._last_failure_message_reported_at = None

        self._failed_keywords: List[dict] = []
        self._source_info_stack: Deque[_SourceInfo] = deque()
        self._ignore_failures_in_stack = IgnoreFailuresInStack()
        self._current_suite_filename = None
        self._current_test_filename = None


_global_events_state = _EventsState()


def _get_events_state():
    return _global_events_state


class EventsListenerV3:
    # Note: see https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
    # for actual attributes.
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self):
        # Whenever it's created, reset the global state.
        global _global_events_state
        _global_events_state = _EventsState()

    # start suite/test
    def start_suite(self, data, result) -> None:
        source = data.source
        name = data.name

        tests = []
        for test in data.tests:
            tests.append(test.name)

        state = _get_events_state()
        state._current_suite_filename = source
        state._source_info_stack.append(_SourceInfo(source, None, None, None, None))

        send_event(StartSuiteEvent(StartSuiteEventBody(name, source, tests)))

    def start_test(self, data, result) -> None:
        state = _get_events_state()

        name = data.name
        source = data.source
        state._current_test_filename = source
        lineno = data.lineno
        state._source_info_stack.append(_SourceInfo(source, lineno, name, None, None))

        send_event(StartTestEvent(StartTestEventBody(name, source, lineno)))

    # end suite/test

    def end_suite(self, data, result) -> None:
        state = _get_events_state()
        try:
            state._current_suite_filename = None
            failed_keywords = tuple(reversed(state._failed_keywords))
            state._failed_keywords = []

            send_event(
                EndSuiteEvent(
                    EndSuiteEventBody(
                        data.name,
                        elapsedtime=result.elapsedtime,
                        status=result.status,
                        source=data.source,
                        message=result.message.strip(),
                        failed_keywords=failed_keywords,
                    )
                )
            )
        finally:
            state._source_info_stack.pop()

    def end_test(self, data, result) -> None:
        state = _get_events_state()
        try:
            state._current_test_filename = None
            lst = []

            if state._failure_messages:
                lst.extend(state._failure_messages)

            msg = "\n".join(lst)

            stripped_msg = result.message.strip()
            if stripped_msg not in msg:
                msg = stripped_msg + "\n" + msg

            state._failure_messages = []
            state._last_failure_message = ""

            failed_keywords = tuple(reversed(state._failed_keywords))
            state._failed_keywords = []

            send_event(
                EndTestEvent(
                    EndTestEventBody(
                        data.name,
                        elapsedtime=result.elapsedtime,
                        status=result.status,
                        source=data.source,
                        message=msg.strip(),
                        failed_keywords=failed_keywords,
                    )
                )
            )
        finally:
            state._source_info_stack.pop()


class EventsListenerV2:
    # Note: see https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
    # for actual attributes.
    ROBOT_LISTENER_API_VERSION = 2

    # For keywords we're just interested on tracking failures to send when a test/suite finished.
    # Note: we also try to capture the failure through logged messages.

    def __init__(self):
        from robotframework_ls.impl.robot_version import get_robot_major_version

        self._robot_major_version = get_robot_major_version()

    def message(self, message):
        if message["level"] in ("FAIL", "ERROR"):
            return self.log_message(message, skip_error=False)

    def log_message(self, message: Dict[str, Any], skip_error=True) -> None:
        """
        Called when an executed keyword writes a log message.

        message is a dictionary with the following contents:

            message: The content of the message.
            level: Log level used in logging the message.
            timestamp: Message creation time in format YYYY-MM-DD hh:mm:ss.mil.
            html: String yes or no denoting whether the message should be interpreted as HTML or not.

        Not called if the message level is below the current threshold level.
        """

        message_string = message.get("message")
        if not message_string:
            return

        level = message["level"]
        if skip_error and level in ("ERROR",):
            # We do this because in RF all the calls to 'log_message'
            # also generate a call to 'message', so, we want to skip
            # one of those (but note that the other way around isn't true
            # and some errors such as import errors are only reported
            # in 'message' and not 'log_message').
            return

        lst = message_string.splitlines(keepends=False)
        if not lst:
            return

        message_string = "\n".join(lst)
        if not message_string.endswith("\n"):
            message_string += "\n"

        state = _get_events_state()

        if state._ignore_failures_in_stack.ignore():
            return

        from robotframework_debug_adapter.message_utils import (
            extract_source_and_line_from_message,
        )

        level = message.get("level")

        source = None
        lineno = None
        test_name = None

        source_and_line = extract_source_and_line_from_message(message_string)
        if source_and_line is not None:
            source, lineno = source_and_line

        if state._source_info_stack:
            from robotframework_debug_adapter import file_utils

            source_info: _SourceInfo

            check = []
            check.append(
                state._source_info_stack[-1]
            )  # Try the real pos, if not possible...
            try:
                check.append(state._source_info_stack[1])  # Use the test
            except IndexError:
                pass
            try:
                check.append(state._source_info_stack[0])  # Use the suite
            except IndexError:
                pass

            for source_info in check:
                test_name = source_info.test_name  # May be None.

                if source is None:
                    source = source_info.source
                    if source is None:
                        continue
                    source = file_utils.get_abs_path_real_path_and_base_from_file(
                        source
                    )[0]

                    try:
                        lineno = source_info.lineno
                    except AttributeError:
                        pass

                if source:
                    break

        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            LogMessageEvent,
            LogMessageEventBody,
        )

        is_failure = message["level"] in ("FAIL", "ERROR")  # FAIL/WARN/INFO/DEBUG/TRACE

        base_message_string = message_string
        if is_failure:
            message_string = f"{message_string}\n{self._print_stack_trace(state)}"

        send_event(
            LogMessageEvent(
                body=LogMessageEventBody(
                    source=source,
                    lineno=lineno,
                    message=f"{message_string}",
                    level=level,
                    testOrSuiteSource=state._current_test_filename
                    or state._current_suite_filename,
                    testName=test_name,
                )
            )
        )

        if is_failure:
            state._failure_messages.append(message_string)
            state._last_failure_message = base_message_string
            state._last_failure_message_full_stacktrace = message_string
            state._last_failure_message_reported_at = (source, lineno)

    def _print_stack_trace(self, state):
        from robotframework_debug_adapter import file_utils
        import linecache

        stack_trace = []
        stack_trace.append("Traceback (most recent call last):")
        found = len(state._source_info_stack) > 0

        source_info: _SourceInfo
        for source_info in state._source_info_stack:
            source = source_info.source
            keyword_name = source_info.keyword_name
            found = True
            if not source:
                stack_trace.append(f"  <unknown source> ({keyword_name})")
                continue
            source = file_utils.get_abs_path_real_path_and_base_from_file(source)[0]
            lineno = source_info.lineno

            line = ""
            try:
                line = linecache.getline(source, lineno).strip()
            except:
                pass

            # We need to put the file in uri format#lineno.
            # see: https://github.com/microsoft/vscode/issues/150702
            source = uris.from_fs_path(source)
            if keyword_name:
                stack_trace.append(f"  {source}#{lineno} ({keyword_name})")
                if line:
                    stack_trace.append(f"    {line}")

            else:
                test_name = source_info.test_name
                if test_name:
                    found = True
                    stack_trace.append(f"  {source}#{lineno} [{test_name}]")
                    if line:
                        stack_trace.append(f"    {line}")

        if not found:
            return ""
        stack_trace.append("")

        return "\n".join(stack_trace)

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        state = _get_events_state()
        state._ignore_failures_in_stack.push(attributes.get("kwname", ""))
        source: Optional[str] = attributes.get("source")
        lineno: Optional[int] = attributes.get("lineno")
        if not source:
            # HACK for RF 3: try to get the location (since it's not available).
            if get_robot_major_version() < 4:
                f: Optional[Any]
                f = sys._getframe()
                while f is not None:
                    if f.f_code.co_name == "run_step":
                        step = f.f_locals.get("step")
                        if step is not None:
                            try:
                                source = step.source
                                lineno = step.lineno
                            except AttributeError:
                                pass
                        break  # Break when run_step is found anyways.

                    f = f.f_back

        test_name = None
        if state._source_info_stack:
            # Keep same test name
            test_name = state._source_info_stack[-1].test_name
        state._source_info_stack.append(
            _SourceInfo(source, lineno, test_name, name, attributes.get("args", ()))
        )

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        state = _get_events_state()
        try:
            source_info: _SourceInfo = state._source_info_stack.pop()
        except:
            log.exception("Error in state._source_info_stack.pop()")
            return
        try:
            if state._ignore_failures_in_stack.ignore():
                return

            status = attributes.get("status")

            # Status could be PASS, FAIL, SKIP or NOT RUN
            if status == "FAIL":
                key = (source_info.source, source_info.lineno)
                if key == state._last_failure_message_reported_at:
                    msg = "[FAIL] " + state._last_failure_message_full_stacktrace
                else:
                    msg = "[FAIL INSIDE] " + state._last_failure_message
                state._failed_keywords.append(
                    {
                        "name": source_info.keyword_name,
                        "source": source_info.source,
                        "lineno": source_info.lineno,
                        "message": msg,
                    }
                )

        finally:
            state._ignore_failures_in_stack.pop()
