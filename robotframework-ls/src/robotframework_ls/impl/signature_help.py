from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from typing import List, Optional, Union


def signature_help(completion_context: ICompletionContext) -> Optional[dict]:
    keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if keyword_definition_and_usage_info is None:
        return None
    current_token = completion_context.get_current_token()
    if current_token is None:
        return None

    from robotframework_ls.impl.keyword_argument_analysis import KeywordArgumentAnalysis
    from robocorp_ls_core.lsp import MarkupContent
    from robocorp_ls_core.lsp import MarkupKind
    from robocorp_ls_core.lsp import SignatureHelp
    from robocorp_ls_core.lsp import SignatureInformation
    from robocorp_ls_core.lsp import ParameterInformation
    from robotframework_ls.impl.protocols import KeywordUsageInfo
    from robotframework_ls.impl.protocols import IKeywordDefinition

    keyword_definition: IKeywordDefinition = keyword_definition_and_usage_info[0]
    usage_info: KeywordUsageInfo = keyword_definition_and_usage_info[1]
    keyword_found: IKeywordFound = keyword_definition.keyword_found

    keyword_args = keyword_found.keyword_args
    keyword_analysis = KeywordArgumentAnalysis(keyword_found)
    active_parameter = keyword_analysis.compute_active_parameter(
        usage_info, lineno=completion_context.sel.line, col=completion_context.sel.col
    )
    docs_format = keyword_found.docs_format

    documentation: Union[str, MarkupContent]
    if docs_format == "markdown":
        documentation = MarkupContent(MarkupKind.Markdown, keyword_found.docs)
    else:
        documentation = keyword_found.docs

    arg_names_as_list: List[str] = []
    parameters: List[ParameterInformation] = []

    for arg in keyword_args:
        arg_names_as_list.append(arg.original_arg)
        parameters.append(
            ParameterInformation(arg.original_arg, None),
        )

    label = "%s(%s)" % (keyword_found.keyword_name, ", ".join(arg_names_as_list))
    signatures: List[SignatureInformation] = [
        SignatureInformation(label, documentation, parameters)
    ]
    return SignatureHelp(
        signatures, active_signature=0, active_parameter=active_parameter
    ).to_dict()
