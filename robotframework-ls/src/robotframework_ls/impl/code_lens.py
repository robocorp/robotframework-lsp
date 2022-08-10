from typing import List

from robocorp_ls_core.lsp import CodeLensTypedDict, RangeTypedDict, PositionTypedDict
from robotframework_ls.impl.protocols import ICompletionContext, NodeInfo
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import ITestInfoTypedDict
from robocorp_ls_core.lsp import CommandTypedDict
from robotframework_ls.impl.robot_constants import ROBOT_FILE_EXTENSIONS

log = get_logger(__name__)


def list_tests(completion_context: ICompletionContext) -> List[ITestInfoTypedDict]:
    from robot.api import Token
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.ast_utils import create_range_from_token

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[ITestInfoTypedDict] = []
    node: NodeInfo
    for node in ast_utils.iter_tests(ast):
        completion_context.check_cancelled()
        try:

            test_case_name_token = node.node.header.get_token(Token.TESTCASE_NAME)
            if not test_case_name_token:
                continue

            ret.append(
                {
                    "uri": completion_context.doc.uri,
                    "path": completion_context.doc.path,
                    "name": test_case_name_token.value,
                    "range": create_range_from_token(test_case_name_token),
                }
            )
        except Exception:
            log.exception("Error listing tests in document.")

    return ret


def code_lens_runs(completion_context: ICompletionContext) -> List[CodeLensTypedDict]:
    from robot.api import Token
    from robotframework_ls.impl.ast_utils import create_range_from_token

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[CodeLensTypedDict] = []

    start: PositionTypedDict = {"line": 0, "character": 0}
    end: PositionTypedDict = {"line": 0, "character": 0}
    code_lens_range: RangeTypedDict = {"start": start, "end": end}

    sections = ast.sections

    test_case_sections = [
        x for x in sections if x.__class__.__name__ == "TestCaseSection"
    ]

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

    for test_case in test_case_sections:
        try:
            for test_node in test_case.body:
                header = getattr(test_node, "header", None)
                if not header:
                    continue
                test_case_name_token = header.get_token(Token.TESTCASE_NAME)
                if not test_case_name_token:
                    continue

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


TEST_CASE_HEADER = "*** Test Case ***\n"


def _iter_rf_interactive_items(ast):
    from robot.api import Token

    sections = ast.sections

    for section in sections:
        if section.__class__.__name__ == "TestCaseSection":
            for node in section.body:
                header = getattr(node, "header", None)
                if header:
                    name_token = header.get_token(Token.TESTCASE_NAME)
                    if name_token:
                        yield name_token, TEST_CASE_HEADER, node

        elif section.__class__.__name__ == "KeywordSection":
            for node in section.body:
                header = getattr(node, "header", None)
                if header:
                    name_token = header.get_token(Token.KEYWORD_NAME)
                    if name_token:
                        yield name_token, "*** Keyword ***\n", node

        elif section.__class__.__name__ == "SettingSection":
            header = getattr(section, "header", None)
            if header:
                name_token = header.get_token(Token.SETTING_HEADER)
                # The header is not needed since it's already a part of its tokens
                # (unlike test cases/keywords)
                if name_token:
                    yield name_token, "", section

        elif section.__class__.__name__ == "VariableSection":
            header = getattr(section, "header", None)
            if header:
                name_token = header.get_token(Token.VARIABLE_HEADER)
                # The header is not needed since it's already a part of its tokens
                # (unlike test cases/keywords)
                if name_token:
                    yield name_token, "", section


def code_lens_rf_interactive(
    completion_context: ICompletionContext,
) -> List[CodeLensTypedDict]:
    from robotframework_ls import import_rf_interactive

    import_rf_interactive()

    ast = completion_context.get_ast()
    completion_context.check_cancelled()

    ret: List[CodeLensTypedDict] = []

    for name_token, header, node in _iter_rf_interactive_items(ast):
        completion_context.check_cancelled()
        ret.append(
            _create_rf_interactive_code_lens(
                completion_context, name_token, header, node
            )
        )

    return ret


def _create_rf_interactive_code_lens(
    completion_context, token, header, node
) -> CodeLensTypedDict:
    from robotframework_ls.impl.ast_utils import create_range_from_token

    code_lens_range = create_range_from_token(token)

    code_lens_dct: CodeLensTypedDict = {
        "range": code_lens_range,
        # Note: initially the command was None and would be resolved later on,
        # but the experience on VSCode appeared sluggish, so, it was changed to
        # always return the command from the start.
        #
        # i.e.: VSCode took too much time to actually do the resolve in some
        # background thread and in the meanwhile it wouldn't show (which makes
        # for a bad experience -- I thought it'd always be there and would
        # resolve just when clicked, but that's not the case).
        # This makes our code-lenses messages bigger, but the processing itself
        # isn't such a big problem and the final experience is better.
        #
        # The code that did the resolution is still there, so, if VSCode
        # improves we can just not return the command here so that it's
        # lazily computed.
        "command": _code_lens_rf_interactive_command(
            header, node, completion_context.doc.uri
        ),
        "data": {"uri": completion_context.doc.uri, "type": "rf_interactive"},
    }
    return code_lens_dct


def _code_lens_rf_interactive_command(header, node, uri) -> CommandTypedDict:
    from robotframework_interactive.ast_to_code import ast_to_code

    code_lens_command: CommandTypedDict = {
        "title": "Run in Interactive Console"
        if header == TEST_CASE_HEADER
        else "Load in Interactive Console",
        "command": "robot.interactiveShell",
        "arguments": [{"code": header + ast_to_code(node), "uri": uri}],
    }
    return code_lens_command


def code_lens_resolve(
    completion_context: ICompletionContext, code_lens: CodeLensTypedDict
):
    # Fill in the command arguments
    command = code_lens.get("command")
    data = code_lens.get("data")
    if (
        command is None
        and isinstance(data, dict)
        and data.get("type") == "rf_interactive"
    ):
        from robotframework_ls import import_rf_interactive

        import_rf_interactive()

        code_lens_range: RangeTypedDict = code_lens["range"]
        code_lens_line = code_lens_range["start"]["line"]

        ast = completion_context.get_ast()
        for name_token, header, node in _iter_rf_interactive_items(ast):
            if name_token.lineno - 1 == code_lens_line:

                code_lens["command"] = _code_lens_rf_interactive_command(
                    header, node, data["uri"]
                )
                break
        else:
            # Unable to resolve
            log.info("Unable to resolve code lens.")
            return code_lens

    return code_lens


def code_lens(completion_context: ICompletionContext) -> List[CodeLensTypedDict]:
    import os
    from robotframework_ls.impl.robot_lsp_constants import (
        OPTION_ROBOT_SHOW_CODE_LENSES,
        OPTION_ROBOT_CODE_LENS_RUN_ENABLE,
        OPTION_ROBOT_CODE_LENS_INTERACTIVE_CONSOLE_ENABLE,
    )

    config = completion_context.config
    if config is not None and not config.get_setting(
        OPTION_ROBOT_SHOW_CODE_LENSES, bool, True
    ):
        return []

    path = completion_context.doc.path
    if not path or not os.path.exists(os.path.dirname(path)):
        # The cwd must exist.
        return []
    if not path.endswith(ROBOT_FILE_EXTENSIONS):
        return []

    code_lenses = []

    if config is None or config.get_setting(
        OPTION_ROBOT_CODE_LENS_RUN_ENABLE, bool, True
    ):
        code_lenses.extend(code_lens_runs(completion_context))

    if config is None or config.get_setting(
        OPTION_ROBOT_CODE_LENS_INTERACTIVE_CONSOLE_ENABLE, bool, True
    ):
        code_lenses.extend(code_lens_rf_interactive(completion_context))
    return code_lenses
