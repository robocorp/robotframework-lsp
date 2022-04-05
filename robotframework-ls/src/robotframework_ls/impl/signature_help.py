from robocorp_ls_core.basic import isinstance_name
from robocorp_ls_core.lsp import MarkupContentTypedDict
from robocorp_ls_core.lsp import MarkupKind
from robocorp_ls_core.lsp import ParameterInformation
from robocorp_ls_core.lsp import SignatureHelp
from robocorp_ls_core.lsp import SignatureInformation
from robotframework_ls.impl.protocols import ICompletionContext, IKeywordFound
from robotframework_ls.impl.protocols import IKeywordDefinition
from robotframework_ls.impl.protocols import KeywordUsageInfo

from typing import List, Optional


def _library_signature_help(
    completion_context: ICompletionContext, library_node
) -> Optional[SignatureHelp]:
    from robotframework_ls.impl import ast_utils
    from robotframework_ls.impl.robot_specbuilder import docs_and_format
    from robot.api import Token
    from robotframework_ls.impl.keyword_argument_analysis import KeywordArgumentAnalysis
    from robotframework_ls.impl.keyword_argument_analysis import (
        UsageInfoForKeywordArgumentAnalysis,
    )
    from robotframework_ls.impl.libspec_manager import LibspecManager

    name = library_node.name
    if not name:
        return None

    libspec_manager: LibspecManager = completion_context.workspace.libspec_manager
    args = ast_utils.get_library_arguments_serialized(library_node)

    library_doc = libspec_manager.get_library_doc_or_error(
        name,
        create=True,
        completion_context=completion_context,
        builtin=False,
        args=args,
    ).library_doc
    if library_doc is None:
        return None

    docs, docs_format = docs_and_format(library_doc)
    documentation: MarkupContentTypedDict = {
        "kind": MarkupKind.Markdown
        if docs_format == "markdown"
        else MarkupKind.PlainText,
        "value": docs,
    }

    arg_names_as_list: List[str] = []
    active_parameter = -1
    parameters: List[ParameterInformation] = []
    for keyword_doc in library_doc.inits:
        for arg in keyword_doc.args:
            arg_names_as_list.append(arg.original_arg)
            parameters.append(
                ParameterInformation(arg.original_arg, None),
            )

        name_token = library_node.get_token(Token.NAME)
        if name_token is not None:
            keyword_analysis = KeywordArgumentAnalysis(keyword_doc.args)
            active_parameter = keyword_analysis.compute_active_parameter(
                UsageInfoForKeywordArgumentAnalysis(library_node, name_token),
                lineno=completion_context.sel.line,
                col=completion_context.sel.col,
            )

        break  # Just add the first one...

    if not arg_names_as_list:
        label = library_doc.name
    else:
        label = "%s(%s)" % (library_doc.name, ", ".join(arg_names_as_list))

    signatures: List[SignatureInformation] = [
        SignatureInformation(label, documentation, parameters)
    ]
    ret = SignatureHelp(
        signatures, active_signature=0, active_parameter=active_parameter
    )
    ret.name = library_doc.name
    ret.node = library_node
    return ret


def signature_help_internal(
    completion_context: ICompletionContext,
) -> Optional[SignatureHelp]:
    token_info = completion_context.get_current_token()
    if token_info is None:
        return None

    if isinstance_name(token_info.node, "LibraryImport"):
        return _library_signature_help(completion_context, token_info.node)

    keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if keyword_definition_and_usage_info is None:
        return None

    from robotframework_ls.impl.keyword_argument_analysis import KeywordArgumentAnalysis
    from robotframework_ls.impl.keyword_argument_analysis import (
        UsageInfoForKeywordArgumentAnalysis,
    )
    from robot.api import Token

    keyword_definition: IKeywordDefinition = keyword_definition_and_usage_info[0]
    usage_info: KeywordUsageInfo = keyword_definition_and_usage_info[1]
    keyword_found: IKeywordFound = keyword_definition.keyword_found

    keyword_args = keyword_found.keyword_args
    keyword_analysis = KeywordArgumentAnalysis(keyword_args)

    keyword_token = usage_info.node.get_token(Token.KEYWORD)

    if keyword_token is None:
        active_parameter = -1
    else:
        active_parameter = keyword_analysis.compute_active_parameter(
            UsageInfoForKeywordArgumentAnalysis(usage_info.node, keyword_token),
            lineno=completion_context.sel.line,
            col=completion_context.sel.col,
        )

    documentation = keyword_found.compute_docs_without_signature()

    arg_names_as_list: List[str] = []
    parameters: List[ParameterInformation] = []

    for arg in keyword_args:
        arg_names_as_list.append(arg.original_arg)
        parameters.append(
            ParameterInformation(arg.original_arg, None),
        )

    if not arg_names_as_list:
        label = keyword_found.keyword_name
    else:
        label = "%s(%s)" % (keyword_found.keyword_name, ", ".join(arg_names_as_list))

    signatures: List[SignatureInformation] = [
        SignatureInformation(label, documentation, parameters)
    ]
    ret = SignatureHelp(
        signatures, active_signature=0, active_parameter=active_parameter
    )
    ret.name = keyword_found.keyword_name
    ret.node = usage_info.node
    return ret


def signature_help(completion_context: ICompletionContext) -> Optional[dict]:
    ret = signature_help_internal(completion_context)
    if ret is None:
        return None

    return ret.to_dict()
