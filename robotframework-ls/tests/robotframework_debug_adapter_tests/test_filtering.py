import os
import pytest


def collect_suite_tests(suite):
    for test in suite.tests:
        yield test
    for s in suite.suites:
        yield from collect_suite_tests(s)


def collect_suite_test_ids(suite, target):
    for test in collect_suite_tests(suite):
        yield (os.path.relpath(test.source, target).replace("\\", "/"), test.name)


@pytest.fixture
def check_sub_init2_suite(dap_resources_dir):
    from robot.api import TestSuite

    target = os.path.join(dap_resources_dir, "check_sub_init2")
    suite = TestSuite.from_file_system(target)
    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 3
    return suite


def create_filtering(include=(), exclude=()):
    from robotframework_debug_adapter.prerun_modifiers import FilteringTestsSuiteVisitor

    visitor = FilteringTestsSuiteVisitor({"include": include, "exclude": exclude})
    return visitor


def test_filtering_with_prerun_modifier_folders(
    dap_resources_dir, check_sub_init2_suite
):
    target = os.path.join(dap_resources_dir, "check_sub_init2")
    suite = check_sub_init2_suite

    visitor = create_filtering([], [])
    visitor.visit_suite(suite)

    # Nothing changes
    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 3

    # Add an include for all (considering subdirs)
    visitor = create_filtering(include=[[target, "*"]])
    visitor.visit_suite(suite)

    # Nothing changes
    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 3

    visitor = create_filtering(exclude=[[target, "*"]])
    visitor.visit_suite(suite)
    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 0


def test_filtering_with_prerun_modifier_tests_1(
    dap_resources_dir, check_sub_init2_suite
):
    target = os.path.join(dap_resources_dir, "check_sub_init2")
    suite = check_sub_init2_suite

    visitor = create_filtering(
        include=[[os.path.join(target, "sub1/my.robot"), "Test case 1"]]
    )
    visitor.visit_suite(suite)

    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 1


def test_filtering_with_prerun_modifier_tests_2(
    dap_resources_dir, check_sub_init2_suite
):
    target = os.path.join(dap_resources_dir, "check_sub_init2")
    suite = check_sub_init2_suite

    visitor = create_filtering(
        exclude=[[os.path.join(target, "sub1/my.robot"), "Test case 1"]]
    )
    visitor.visit_suite(suite)

    found = list(collect_suite_test_ids(suite, target))
    assert len(found) == 2
