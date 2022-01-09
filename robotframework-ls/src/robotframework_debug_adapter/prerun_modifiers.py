from robot.api import SuiteVisitor
import os
import json
from typing import Set, Dict

from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


class FilteringTestsSuiteVisitor(SuiteVisitor):
    def __init__(self) -> None:
        super().__init__()
        # filename -> test names
        self.include: Dict[str, Set[str]] = {}
        self.exclude: Dict[str, Set[str]] = {}

        tests_filtering = os.getenv("RFLS_PRERUN_FILTER_TESTS", "")

        def add(tup, container):
            source, test_name = tup
            source = self._normalize(source)
            s = container.get(source)
            if s is None:
                s = container[source] = set()
            s.add(test_name)

        if tests_filtering:
            log.info("Found tests filtering: %s", tests_filtering)
            loaded = json.loads(tests_filtering)
            for tup in loaded["include"]:
                add(tup, self.include)
            for tup in loaded["exclude"]:
                add(tup, self.exclude)

    def _normalize(self, source):
        return os.path.normcase(os.path.normpath(os.path.abspath(source)))

    def start_suite(self, suite) -> None:
        new_tests = []
        for t in suite.tests:
            source = self._normalize(t.source)

            if self.include:
                test_names = self.include.get(source)
                if test_names is None:
                    log.debug("Test source not in includes: %s - %s", t.source, t.name)
                    continue
                if t.name not in test_names:
                    log.debug("Test name not in includes: %s - %s", t.source, t.name)
                    continue

            # If we got here it's included, now, check excludes.
            if self.exclude:
                test_names = self.exclude.get(source)
                if test_names and t.name in test_names:
                    log.debug("Test in excludes: %s - %s", t.source, t.name)
                    continue

            new_tests.append(t)
        suite.tests = new_tests

    def end_suite(self, suite):
        # We don't want to keep empty suites.
        suite.suites = [s for s in suite.suites if s.test_count > 0]
