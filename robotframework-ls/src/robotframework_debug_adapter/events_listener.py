from typing import Any, Dict, List, Optional
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


def send_event(event):
    from robotframework_debug_adapter.global_vars import get_global_robot_target_comm

    robot_target_comm = get_global_robot_target_comm()
    if robot_target_comm is not None:
        robot_target_comm.write_message(event)


class EventsListenerV2:
    # Note: see https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
    # for actual attributes.
    ROBOT_LISTENER_API_VERSION = "2"

    def __init__(self) -> None:
        self._failed_keywords: Optional[List[Dict[str, Any]]] = None
        self._keyword_failure_messages: List[str] = []

    # start suite/test

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        source = attributes.get("source")
        tests = attributes.get("tests")
        send_event(StartSuiteEvent(StartSuiteEventBody(name, source, tests)))

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        self._failed_keywords = None

        source = attributes.get("source")
        lineno = attributes.get("lineno")
        tests = attributes.get("tests")
        send_event(
            StartTestEvent(
                StartTestEventBody(
                    attributes.get("originalname") or name, source, lineno
                )
            )
        )

    # end suite/test

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        send_event(
            EndSuiteEvent(
                EndSuiteEventBody(
                    name,
                    elapsedtime=attributes.get("elapsedtime"),
                    status=attributes.get("status"),
                    source=attributes.get("source"),
                    message=attributes.get("message"),
                    failed_keywords=self._failed_keywords,
                )
            )
        )
        self._failed_keywords = None

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        send_event(
            EndTestEvent(
                EndTestEventBody(
                    attributes.get("originalname") or name,
                    elapsedtime=attributes.get("elapsedtime"),
                    status=attributes.get("status"),
                    source=attributes.get("source"),
                    message=attributes.get("message"),
                    failed_keywords=self._failed_keywords,
                )
            )
        )

        self._failed_keywords = None

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
        if message["level"] == "FAIL":  # FAIL/WARN/INFO/DEBUG/TRACE
            self._keyword_failure_messages.append(message["message"])

    message = log_message

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        self._keyword_failure_messages = []

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
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
                    "failure_messages": self._keyword_failure_messages,
                }
            )
