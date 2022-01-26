from typing import Any, Dict, List, Optional, Deque
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


def send_event(event):
    from robotframework_debug_adapter.global_vars import get_global_robot_target_comm

    robot_target_comm = get_global_robot_target_comm()
    if robot_target_comm is not None:
        robot_target_comm.write_message(event)


_SourceInfo = namedtuple("_SourceInfo", "source, lineno, test_name")


class EventsListenerV2:
    # Note: see https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
    # for actual attributes.
    ROBOT_LISTENER_API_VERSION = "2"

    def __init__(self) -> None:
        from collections import deque

        self._failed_keywords: Optional[List[Dict[str, Any]]] = None
        self._failure_messages: List[str] = []
        self._add_to_test_failure: str = ""
        self._source_info_stack: Deque[_SourceInfo] = deque()

    # start suite/test

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source")
        tests = attributes.get("tests")
        self._source_info_stack.append(_SourceInfo(source, None, None))

        send_event(StartSuiteEvent(StartSuiteEventBody(name, source, tests)))

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        if self._failure_messages:
            self._add_to_test_failure = "\n".join(self._failure_messages)
            self._failure_messages = []

        name = attributes.get("originalname") or name
        source = attributes.get("source")
        lineno = attributes.get("lineno")
        self._source_info_stack.append(_SourceInfo(source, lineno, name))

        send_event(StartTestEvent(StartTestEventBody(name, source, lineno)))

    # end suite/test

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        try:
            send_event(
                EndSuiteEvent(
                    EndSuiteEventBody(
                        name,
                        elapsedtime=attributes.get("elapsedtime"),
                        status=attributes.get("status"),
                        source=attributes.get("source"),
                        message=attributes.get("message", "").strip(),
                        failed_keywords=self._failed_keywords,
                    )
                )
            )
        finally:
            self._failed_keywords = None
            self._source_info_stack.pop()

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        try:
            msg = attributes.get("message", "")
            if self._add_to_test_failure:
                msg = self._add_to_test_failure + "\n" + msg
                self._add_to_test_failure = ""

            if self._failure_messages:
                if msg:
                    msg += "\n"
                msg += "\n".join(self._failure_messages)
                self._failure_messages = []

            send_event(
                EndTestEvent(
                    EndTestEventBody(
                        attributes.get("originalname") or name,
                        elapsedtime=attributes.get("elapsedtime"),
                        status=attributes.get("status"),
                        source=attributes.get("source"),
                        message=msg.strip(),
                        failed_keywords=self._failed_keywords,
                    )
                )
            )
        finally:
            self._failed_keywords = None
            self._source_info_stack.pop()

    # For keywords we're just interested on tracking failures to send when a test/suite finished.
    # Note: we also try to capture the failure through logged messages.

    def log_message(self, message: Dict[str, Any]) -> None:
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

        if self._source_info_stack:
            from robotframework_debug_adapter import file_utils

            source_info: _SourceInfo = self._source_info_stack[-1]
            test_name = source_info.test_name  # May be None.

            if source is None:
                source = source_info.source
                source = file_utils.get_abs_path_real_path_and_base_from_file(source)[0]

            if lineno is None:
                lineno = 0
                try:
                    lineno = source_info.lineno
                except AttributeError:
                    pass

        from robocorp_ls_core.debug_adapter_core.dap.dap_schema import (
            LogMessageEvent,
            LogMessageEventBody,
        )

        send_event(
            LogMessageEvent(
                body=LogMessageEventBody(
                    source=source,
                    lineno=lineno,
                    message=f"{message_string}",
                    level=level,
                    testName=test_name,
                )
            )
        )

        if message["level"] in ("FAIL", "ERROR"):  # FAIL/WARN/INFO/DEBUG/TRACE
            self._failure_messages.append(message["message"])

    def message(self, message):
        if message["level"] in ("FAIL", "ERROR"):
            # We also want to show these for system messages.
            return self.log_message(message)

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source")
        lineno = attributes.get("lineno")
        test_name = None
        if self._source_info_stack:
            # Keep same test name
            test_name = self._source_info_stack[-1].test_name
        self._source_info_stack.append(_SourceInfo(source, lineno, test_name))

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        try:
            status = attributes.get("status")
            # Status could be PASS, FAIL, SKIP or NOT RUN. SKIP and NOT RUN
            if status == "FAIL":
                if self._failed_keywords is None:
                    self._failed_keywords = []
                source = attributes.get("source")
                if not source:
                    return
                lineno = attributes.get("lineno")
                if lineno is None:
                    return

                self._failed_keywords.append(
                    {
                        "name": name,
                        "source": source,
                        "lineno": lineno,
                        "failure_messages": self._failure_messages,
                    }
                )
                self._failure_messages = []
        finally:
            self._source_info_stack.pop()
