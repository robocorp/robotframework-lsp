from robocorp_ls_core.protocols import ILanguageServerClient
import os
from robotframework_ls.commands import ROBOT_START_INDEXING_INTERNAL


def test_explore_tests(language_server_io: ILanguageServerClient, workspace_dir, cases):
    cases.copy_to("case_multiple_tests", workspace_dir)
    language_server = language_server_io
    language_server.initialize(workspace_dir, process_id=os.getpid())

    message_matcher = language_server.obtain_pattern_message_matcher(
        {"method": "$/testsCollected"}
    )

    language_server.execute_command(ROBOT_START_INDEXING_INTERNAL, [])

    from robocorp_ls_core.unittest_tools.fixtures import TIMEOUT

    assert message_matcher.event.wait(TIMEOUT)
