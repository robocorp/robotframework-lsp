from robocorp_ls_core.protocols import ILanguageServerClient
import os
from robocorp_ls_core import uris


def test_explore_tests(language_server_io: ILanguageServerClient, workspace_dir, cases):
    from robotframework_ls.commands import ROBOT_START_INDEXING_INTERNAL
    from robotframework_ls.commands import ROBOT_WAIT_FIRST_TEST_COLLECTION_INTERNAL

    cases.copy_to("case_multiple_tests", workspace_dir)
    language_server = language_server_io
    language_server.initialize(workspace_dir, process_id=os.getpid())

    tests_collected = {}

    def on_message(msg):
        if msg.get("method") == "$/testsCollected":
            params = msg["params"]
            uri = params["uri"]
            test_info = params["testInfo"]
            basename = os.path.basename(uris.to_fs_path(uri))
            tests_collected[basename] = test_info

    language_server.on_message.register(on_message)
    language_server.execute_command(ROBOT_START_INDEXING_INTERNAL, [])

    for _i in range(2):
        # In the 2nd it doesn't really do anything...
        assert language_server.execute_command(
            ROBOT_WAIT_FIRST_TEST_COLLECTION_INTERNAL, []
        )

    assert tests_collected == {
        "robot1.robot": [
            {
                "name": "Can use package",
                "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 15},
                },
            }
        ],
        "robot2.robot": [
            {
                "name": "Can use package",
                "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 15},
                },
            }
        ],
        "robot3.robot": [
            {
                "name": "Test1",
                "range": {
                    "start": {"line": 1, "character": 0},
                    "end": {"line": 1, "character": 5},
                },
            },
            {
                "name": "Test2",
                "range": {
                    "start": {"line": 4, "character": 0},
                    "end": {"line": 4, "character": 5},
                },
            },
        ],
    }
