from typing import List

from robocorp_ls_core.lsp import (
    CommandTypedDict,
    ICustomDiagnosticDataTypedDict,
    ICustomDiagnosticDataUndefinedKeywordTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext
import typing


def code_action(
    completion_context: ICompletionContext,
    found_data: List[ICustomDiagnosticDataTypedDict],
) -> List[CommandTypedDict]:
    ret: List[CommandTypedDict] = []
    for data in found_data:
        if data["kind"] == "undefined_keyword":
            undefined_keyword_data = typing.cast(
                ICustomDiagnosticDataUndefinedKeywordTypedDict, data
            )
            command: CommandTypedDict = {
                "title": "Create keyword",
                "command": "some command",
                "arguments": [],
            }

            ret.append(command)

            command2: CommandTypedDict = {
                "title": "Add import",
                "command": "some command2",
                "arguments": [],
            }

            ret.append(command2)

    return ret
