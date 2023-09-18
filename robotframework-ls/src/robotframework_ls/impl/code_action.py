from typing import Set, List, Optional

from robocorp_ls_core.lsp import (
    Range,
    CodeActionTypedDict,
    ICustomDiagnosticDataTypedDict,
    TextDocumentContextTypedDict,
)
from robotframework_ls.impl.protocols import ICompletionContext


def code_action_all(
    completion_context: ICompletionContext,
    select_range: Range,
    only: Set[str],
    context: TextDocumentContextTypedDict,
) -> List[CodeActionTypedDict]:
    from robotframework_ls.impl.code_action_refactoring import (
        code_action_refactoring,
    )
    from robotframework_ls.impl.code_action_quickfix import code_action_quickfix
    from robotframework_ls.impl.code_action_others import (
        code_action_others,
        code_action_surround_with,
    )

    # See:
    # codeActionProvider.codeActionKinds
    # at:
    # robotframework_ls.robotframework_ls_impl.RobotFrameworkLanguageServer.capabilities
    # to see what may be included in 'only'

    ret: List[CodeActionTypedDict] = []
    ret.extend(code_action_refactoring(completion_context, select_range, only))

    if not only or (only and "quickfix" in only):
        found_data: List[ICustomDiagnosticDataTypedDict] = []
        diagnostics = context.get("diagnostics")
        if diagnostics:
            for diagnostic in diagnostics:
                data: Optional[ICustomDiagnosticDataTypedDict] = diagnostic.get("data")
                if data is not None:
                    found_data.append(data)
        ret.extend(code_action_quickfix(completion_context, found_data))

    ret.extend(code_action_others(completion_context, select_range, only))
    ret.extend(code_action_surround_with(completion_context, select_range, only))
    return ret
