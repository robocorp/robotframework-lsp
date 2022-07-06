from typing import Set, Optional
import os
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robocorp_ls_core.options import is_true_in_env
import sys
from robotframework_ls.impl.robot_version import get_robot_major_version

log = get_logger(__name__)


class IgnoreFailuresInStack:
    """
    We load the contents from environment variables:

    RFLS_IGNORE_FAILURES_IN_KEYWORDS:
        A (json-formatted) list of keywords where failures should be ignored.
        Note: ignored means they won't be reported as errors and the debugger
        won't break on them.

    The list below is always ignored by default (so using RFLS_IGNORE_FAILURES_IN_KEYWORDS
    it's possible to add other items to that list).

    [
        "run keyword and continue on failure",
        "run keyword and expect error",
        "run keyword and ignore error",
        "run keyword and warn on failure",
        "wait until keyword succeeds",
        "try..except",
    ]

    It's also possible to set `RFLS_IGNORE_FAILURES_IN_KEYWORDS_OVERRIDE=1` to provide
    all the items if one of those shouldn't be there.
    """

    def __init__(self):
        import json
        from collections import deque

        self._stack: "Deque[str]" = deque()
        self.ignore_failures_inside: Set[str] = set()

        # Add default excludes.
        for entry in (
            "run keyword and continue on failure",
            "run keyword and expect error",
            "run keyword and ignore error",
            "run keyword and warn on failure",
            "wait until keyword succeeds",
            "run keyword and return status",
            "try..except",
        ):
            self.ignore_failures_inside.add(normalize_robot_name(entry))

        if is_true_in_env("RFLS_IGNORE_FAILURES_IN_KEYWORDS_OVERRIDE"):
            self.ignore_failures_inside.clear()

        # Load additional excludes from the environment.
        ignore_failures_inside_in_env = os.getenv("RFLS_IGNORE_FAILURES_IN_KEYWORDS")
        if ignore_failures_inside_in_env:
            try:
                loaded = json.loads(ignore_failures_inside_in_env)
            except:
                log.exception(
                    "Error: unable to load RFLS_IGNORE_FAILURES_IN_KEYWORDS (%s) as a json.",
                    ignore_failures_inside_in_env,
                )
            else:
                if not isinstance(loaded, list):
                    log.critical(
                        "Expected RFLS_IGNORE_FAILURES_IN_KEYWORDS to be a json list of strings. Found: %s",
                        type(loaded),
                    )

                else:

                    for entry in loaded:
                        self.ignore_failures_inside.add(normalize_robot_name(entry))

    def ignore(self) -> bool:
        from types import FrameType

        for name in self._stack:
            normalized = normalize_robot_name(name)
            if normalized in self.ignore_failures_inside:
                return True

        if get_robot_major_version() >= 5:
            # Allow for try..except in RF 5.
            if "try..except" in self.ignore_failures_inside:
                curframe: Optional[FrameType] = sys._getframe()
                while curframe is not None:
                    # RF makes the try..except invisible for us.
                    # The listener specifically skips it in
                    # robot.output.listeners.Listeners.start_keyword
                    # So, our approach is search whether we're inside some try..except
                    # using the current stack.
                    if curframe.f_code.co_name == "_run_try":
                        return True
                    curframe = curframe.f_back
        return False

    def push(self, name: str):
        self._stack.append(name)

    def pop(self):
        try:
            self._stack.pop()
        except:
            log.exception("Error in IgnoreFailuresInStack.pop()")
