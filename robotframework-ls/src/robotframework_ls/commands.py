# fmt: off
# Warning: Don't edit file (autogenerated from python -m dev codegen).
from typing import List

ROBOT_RUN_TEST = "robot.runTest"  # Run Test/Task
ROBOT_DEBUG_TEST = "robot.debugTest"  # Debug Test/Task
ROBOT_RUN_SUITE = "robot.runSuite"  # Run Tests/Tasks Suite
ROBOT_DEBUG_SUITE = "robot.debugSuite"  # Debug Tests/Tasks Suite
ROBOT_INTERACTIVE_SHELL = "robot.interactiveShell"  # Start Interactive Console
ROBOT_INTERNAL_RFINTERACTIVE_START = "robot.internal.rfinteractive.start"  # Create Interactive Console
ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE = "robot.internal.rfinteractive.evaluate"  # Evaluate in Interactive Console
ROBOT_INTERNAL_RFINTERACTIVE_STOP = "robot.internal.rfinteractive.stop"  # Stop Interactive Console
ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS = "robot.internal.rfinteractive.semanticTokens"  # Get the semantic tokens based on the code entered.
ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION = "robot.internal.rfinteractive.resolveCompletion"  # Resolves the passed completion.
ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS = "robot.internal.rfinteractive.completions"  # Get the completions based on the code entered.
ROBOT_GET_RFLS_HOME_DIR = "robot.getRFLSHomeDir"  # Provides the directory used to store information (usually ~/.robotframework-ls -- may be configured with `ROBOTFRAMEWORK_LS_USER_HOME` environment variable).
ROBOT_CLEAR_CACHES_AND_RESTART_PROCESSES = "robot.clearCachesAndRestartProcesses"  # Clear caches and restart Robot Framework Language Server processes
ROBOT_CLEAR_CACHES_AND_RESTART_PROCESSES_START_INTERNAL = "robot.clearCachesAndRestartProcesses.start.internal"  # Stops the RFLS and waits for robot.clearCachesAndRestartProcesses.finish.internal to restart
ROBOT_CLEAR_CACHES_AND_RESTART_PROCESSES_FINISH_INTERNAL = "robot.clearCachesAndRestartProcesses.finish.internal"  # To be used to restart the processes
ROBOT_START_INDEXING_INTERNAL = "robot.startIndexing.internal"  # Starts the indexing service
ROBOT_WAIT_FULL_TEST_COLLECTION_INTERNAL = "robot.waitFullTestCollection.internal"  # Schedules and Waits for a full test collection

ALL_SERVER_COMMANDS: List[str] = [
    ROBOT_INTERNAL_RFINTERACTIVE_START,
    ROBOT_INTERNAL_RFINTERACTIVE_EVALUATE,
    ROBOT_INTERNAL_RFINTERACTIVE_STOP,
    ROBOT_INTERNAL_RFINTERACTIVE_SEMANTIC_TOKENS,
    ROBOT_INTERNAL_RFINTERACTIVE_RESOLVE_COMPLETION,
    ROBOT_INTERNAL_RFINTERACTIVE_COMPLETIONS,
    ROBOT_GET_RFLS_HOME_DIR,
    ROBOT_START_INDEXING_INTERNAL,
    ROBOT_WAIT_FULL_TEST_COLLECTION_INTERNAL,
]

# fmt: on
