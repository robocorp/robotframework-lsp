from robot.api import SuiteVisitor
import os
import json
from typing import Set, Dict, Optional

from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.basic import normalize_filename

log = get_logger(__name__)


class FilteringTestsSuiteVisitor(SuiteVisitor):
    def __init__(
        self, tests_filtering: Optional[Dict[str, Dict[str, Set[str]]]] = None
    ) -> None:
        log.info("Initializing FilteringTestsSuiteVisitor")
        super().__init__()
        # filename -> test names
        self.include: Dict[str, Set[str]] = {}
        self.exclude: Dict[str, Set[str]] = {}

        self._include_contains_cache: dict = {}
        self._exclude_contains_cache: dict = {}

        if tests_filtering is not None:
            log.info(
                "FilteringTestsSuiteVisitor initial tests_filtering: %s",
                tests_filtering,
            )
        else:
            s = os.getenv("RFLS_PRERUN_FILTER_TESTS", None)
            if s is None:
                log.info(
                    "RFLS_PRERUN_FILTER_TESTS not specified in environment variables."
                )
            elif not s:
                log.info("RFLS_PRERUN_FILTER_TESTS empty in environment variables.")
            else:
                log.info("RFLS_PRERUN_FILTER_TESTS environment variable value: %s", s)
                try:
                    tests_filtering = json.loads(s)
                except:
                    log.exception("Error parsing RFLS_PRERUN_FILTER_TESTS as json")

        def add(tup, container):
            source, test_name = tup
            source = self._normalize(source)
            s = container.get(source)
            if s is None:
                s = container[source] = set()
            s.add(test_name)

        if tests_filtering:
            for tup in tests_filtering.get("include", []):
                add(tup, self.include)
            for tup in tests_filtering.get("exclude", []):
                add(tup, self.exclude)

    def _normalize(self, source):
        return normalize_filename(source)

    def _contains(
        self, container: dict, source: str, test_name: str, cache: dict
    ) -> bool:
        # Note: we have a cache because _contains_uncached will always check
        # the parent structure for hits and whenever we find a hit we
        # can skip it.
        key = (source, test_name)
        ret = cache.get(key)
        if ret is not None:
            return ret

        ret = self._contains_uncached(container, source, test_name, cache)
        cache[key] = ret
        return ret

    def _contains_uncached(
        self, container: dict, source: str, test_name: str, cache: dict
    ) -> bool:
        # Try to check for the test directly
        test_names = container.get(source)
        if not test_names:
            dirname = os.path.dirname(source)
            if dirname == source or not dirname:
                return False

            return self._contains(
                container,
                dirname,
                "*",  # at a parent level the test name doesn't matter
                cache,
            )

        if "*" in test_names:
            return True
        if test_name != "*":
            return test_name in test_names
        return False

    def start_suite(self, suite) -> None:
        new_tests = []
        for t in suite.tests:
            source = self._normalize(t.source)

            if self.include:
                if not self._contains(
                    self.include, source, t.name, self._include_contains_cache
                ):
                    log.debug("Test not in includes: %s - %s", t.source, t.name)
                    continue

            # If we got here it's included, now, check excludes.
            if self.exclude:
                if self._contains(
                    self.exclude, source, t.name, self._exclude_contains_cache
                ):
                    log.debug("Test in excludes: %s - %s", t.source, t.name)
                    continue

            new_tests.append(t)
        suite.tests = new_tests

    def end_suite(self, suite):
        # We don't want to keep empty suites.
        suite.suites = [s for s in suite.suites if s.test_count > 0]
