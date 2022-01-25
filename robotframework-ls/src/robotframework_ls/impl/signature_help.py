from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from typing import List, Optional, Union


def signature_help(completion_context: ICompletionContext) -> Optional[dict]:
    from robocorp_ls_core.lsp import MarkupContent
    from robocorp_ls_core.lsp import MarkupKind

    keyword_definition = completion_context.get_current_keyword_definition()
    if keyword_definition is not None:

        from robocorp_ls_core.lsp import SignatureHelp
        from robocorp_ls_core.lsp import SignatureInformation
        from robocorp_ls_core.lsp import ParameterInformation

        keyword_found: IKeywordFound = keyword_definition.keyword_found

        keyword_args = keyword_found.keyword_args
        lst = [arg.original_arg for arg in keyword_args]

        label = "%s(%s)" % (keyword_found.keyword_name, ", ".join(lst))
        docs_format = keyword_found.docs_format

        documentation: Union[str, MarkupContent]
        if docs_format == "markdown":
            documentation = MarkupContent(MarkupKind.Markdown, keyword_found.docs)
        else:
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
