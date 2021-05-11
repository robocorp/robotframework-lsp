from typing import List

from robocorp_ls_core.lsp import CodeLensTypedDict
from robotframework_ls.impl.protocols import ICompletionContext, NodeInfo
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def code_lens(completion_context: ICompletionContext) -> List[CodeLensTypedDict]:
    from robotframework_ls.impl import ast_utils
    from robocorp_ls_core.lsp import RangeTypedDict, PositionTypedDict, CommandTypedDict
    from robotframework_ls.impl import robot_constants

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[CodeLensTypedDict] = []
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

            start: PositionTypedDict = {
                "line": test_case_name_token.lineno - 1,
                "character": test_case_name_token.col_offset,
            }
            end: PositionTypedDict = {
                "line": test_case_name_token.lineno - 1,
                "character": test_case_name_token.end_col_offset,
            }
            code_lens_range: RangeTypedDict = {"start": start, "end": end}

            command: CommandTypedDict = {
                "title": "Run",
                "command": "robot.run",
                "arguments": [
                    {
                        "uri": completion_context.doc.uri,
                        "name": test_case_name_token.value,
                    }
                ],
            }

            code_lens_dct: CodeLensTypedDict = {
                "range": code_lens_range,
                "command": command,
            }
            ret.append(code_lens_dct)

            command = {
                "title": "Debug",
                "command": "robot.debug",
                "arguments": [
                    {"uri": completion_context.doc.uri, "name": node.node.name}
                ],
            }

            code_lens_dct = {"range": code_lens_range, "command": command}
            ret.append(code_lens_dct)
        except Exception:
            log.exception("Error computing code lens")

    return ret
