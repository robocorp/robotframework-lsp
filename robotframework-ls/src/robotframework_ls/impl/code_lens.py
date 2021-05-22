from typing import List

from robocorp_ls_core.lsp import CodeLensTypedDict
from robotframework_ls.impl.protocols import ICompletionContext, NodeInfo
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import ITestInfoTypedDict

log = get_logger(__name__)


def list_tests(completion_context: ICompletionContext) -> List[ITestInfoTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl import robot_constants

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[ITestInfoTypedDict] = []
    node: NodeInfo
    for node in ast_utils.iter_tests(ast):
        completion_context.check_cancelled()
        try:

            test_case_name_token = node.node.header.get_token(
                robot_constants.TESTCASE_NAME
            )
            if test_case_name_token is None:
                # Old versions have slashes and not spaces as a separator.
                test_case_name_token = node.node.header.get_token(
                    robot_constants.TESTCASE_NAME.replace(" ", "_")
                )

            ret.append(
                {
                    "uri": completion_context.doc.uri,
                    "path": completion_context.doc.path,
                    "name": test_case_name_token.value,
                }
            )
        except Exception:
            log.exception("Error listing tests in document.")

    return ret


def code_lens(completion_context: ICompletionContext) -> List[CodeLensTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import CommandTypedDict
    from robot.api import Token  # noqa
    from robocorp_ls_core.lsp import PositionTypedDict
    from robocorp_ls_core.lsp import RangeTypedDict
    from robotframework_ls.impl.ast_utils import create_range_from_token

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[CodeLensTypedDict] = []
    node_info: NodeInfo

    start: PositionTypedDict = {"line": 0, "character": 0}
    end: PositionTypedDict = {"line": 0, "character": 0}
    code_lens_range: RangeTypedDict = {"start": start, "end": end}

    test_case_sections = list(ast_utils.iter_test_case_sections(ast))

    if len(test_case_sections) > 0:
        # Run Test command
        command: CommandTypedDict = {
            "title": "Run Suite",
            "command": "robot.runTest",
            "arguments": [
                {
                    "uri": completion_context.doc.uri,
                    "path": completion_context.doc.path,
                    "name": "*",
                }
            ],
        }

        ret.append({"range": code_lens_range, "command": command})

        # Debug Test command
        command = {
            "title": "Debug Suite",
            "command": "robot.debugTest",
            "arguments": [
                {
                    "uri": completion_context.doc.uri,
                    "path": completion_context.doc.path,
                    "name": "*",
                }
            ],
        }

        ret.append({"range": code_lens_range, "command": command})

    for node_info in test_case_sections:
        try:
            for test_node in node_info.node.body:
                test_case_name_token = test_node.header.get_token(Token.TESTCASE_NAME)
                completion_context.check_cancelled()

                code_lens_range = create_range_from_token(test_case_name_token)

                # Run Test command
                command = {
                    "title": "Run",
                    "command": "robot.runTest",
                    "arguments": [
                        {
                            "uri": completion_context.doc.uri,
                            "path": completion_context.doc.path,
                            "name": test_case_name_token.value,
                        }
                    ],
                }

                code_lens_dct: CodeLensTypedDict = {
                    "range": code_lens_range,
                    "command": command,
                }
                ret.append(code_lens_dct)

                # Debug Test command
                command = {
                    "title": "Debug",
                    "command": "robot.debugTest",
                    "arguments": [
                        {
                            "uri": completion_context.doc.uri,
                            "path": completion_context.doc.path,
                            "name": test_node.name,
                        }
                    ],
                }

                code_lens_dct = {"range": code_lens_range, "command": command}
                ret.append(code_lens_dct)
        except Exception:
            log.exception("Error computing code lens")

    return ret
