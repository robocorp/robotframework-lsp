from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from typing import List, Optional


def signature_help(completion_context: ICompletionContext) -> Optional[dict]:
    from robotframework_ls.impl.find_definition import find_keyword_definition
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.protocols import TokenInfo
    from robotframework_ls.impl.protocols import IKeywordDefinition

    token_info = completion_context.get_current_token()
    if token_info is not None:
        usage_info = ast_utils.create_keyword_usage_info(
            token_info.stack, token_info.node
        )
        if usage_info is not None:
            token = usage_info.token

            # token line is 1-based and col is 0-based (make both 0-based here).
            line = token.lineno - 1
            col = token.col_offset
            cp = completion_context.create_copy_with_selection(line, col)
            definitions = find_keyword_definition(
                cp, TokenInfo(usage_info.stack, usage_info.node, usage_info.token)
            )
            if definitions and len(definitions) >= 1:
                definition: IKeywordDefinition = next(iter(definitions))
                keyword_found: IKeywordFound = definition.keyword_found

                from robocorp_ls_core.lsp import SignatureHelp
                from robocorp_ls_core.lsp import SignatureInformation
                from robocorp_ls_core.lsp import ParameterInformation

                keyword_args = keyword_found.keyword_args
                label = "%s(%s)" % (keyword_found.keyword_name, ", ".join(keyword_args))
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
