from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from typing import List, Optional


def signature_help(completion_context: ICompletionContext) -> Optional[dict]:
    keyword_definition = completion_context.get_current_keyword_definition()
    if keyword_definition is not None:

        from robocorp_ls_core.lsp import SignatureHelp
        from robocorp_ls_core.lsp import SignatureInformation
        from robocorp_ls_core.lsp import ParameterInformation

        keyword_found: IKeywordFound = keyword_definition.keyword_found

        keyword_args = keyword_found.keyword_args
        lst = [arg.original_arg for arg in keyword_args]

        label = "%s(%s)" % (keyword_found.keyword_name, ", ".join(lst))
        documentation = keyword_found.docs
        parameters: List[ParameterInformation] = [
            # Note: the label here is to highlight a part of the main signature label!
            # (let's leave this out for now)
            # ParameterInformation("param1", None),
        ]
        signatures: List[SignatureInformation] = [
            SignatureInformation(label, documentation, parameters)
        ]
        return SignatureHelp(
            signatures, active_signature=0, active_parameter=0
        ).to_dict()

    return None
