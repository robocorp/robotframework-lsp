from robocorp_ls_core.lsp import (
    HoverTypedDict,
    MarkupKind,
    SignatureHelp,
    SignatureInformation,
    MarkupContentTypedDict,
)
from typing import Optional
from robotframework_ls.impl.protocols import ICompletionContext


def hover(completion_context: ICompletionContext) -> Optional[HoverTypedDict]:
    from robotframework_ls.impl.find_definition import find_definition_extended
    from robotframework_ls.impl import ast_utils

    definition_info = find_definition_extended(completion_context)
    if definition_info:
        for definition in definition_info.definitions:
            if hasattr(definition, "keyword_found"):
                # If we found a keyword use the signature help.
                break

            return {
                "contents": definition.hover_docs(),
                "range": definition_info.origin_selection_range,
            }

    from robotframework_ls.impl.signature_help import signature_help_internal

    sig_help: Optional[SignatureHelp] = signature_help_internal(completion_context)
    if sig_help is None:
        return None

    node = sig_help.node
    signatures = sig_help.signatures
    if not signatures:
        return None
    try:
        active_signature: SignatureInformation = signatures[sig_help.activeSignature]
    except IndexError:
        active_signature = signatures[0]

    active_parameter = sig_help.activeParameter

    optional_documentation_markup: Optional[
        MarkupContentTypedDict
    ] = active_signature.documentation
    documentation_markup: MarkupContentTypedDict
    if not optional_documentation_markup:
        documentation_markup = {"kind": MarkupKind.Markdown, "value": ""}
    else:
        documentation_markup = optional_documentation_markup
    kind = documentation_markup["kind"]

    # Now, let's add the signature to the documentation
    escape = lambda s: s

    if kind == MarkupKind.Markdown:
        from robotframework_ls import html_to_markdown

        escape = html_to_markdown.escape

    add_documentation = True
    if kind == MarkupKind.Markdown:
        signature_doc = ["**", escape(sig_help.name), "**"]
    else:
        signature_doc = [sig_help.name]

    if kind == MarkupKind.Markdown:
        prefix_highlight = "*`"
        postfix_highlight = "`*"
    else:
        prefix_highlight = "`"
        postfix_highlight = "`"

    if active_signature.parameters:
        signature_doc.append("(")
        for i, parameter in enumerate(active_signature.parameters):
            if i > 0:
                signature_doc.append(", ")

            escaped_label = escape(parameter.label)
            if i == active_parameter:
                add_documentation = False
                signature_doc.insert(
                    0,
                    f"Parameter: {prefix_highlight}{escaped_label}{postfix_highlight} in Keyword Call.\n\n",
                )

                signature_doc.append(prefix_highlight)

            signature_doc.append(escaped_label)

            if i == active_parameter:
                signature_doc.append(postfix_highlight)

        signature_doc.append(")")

    if add_documentation:
        # When over a parameter, don't add the documentation.
        signature_doc.append("\n\n")
        signature_doc.append(documentation_markup["value"])

    token_info = completion_context.get_current_token()
    if token_info and token_info.token:
        show_range = ast_utils.create_range_from_token(token_info.token)
    else:
        show_range = {
            "start": {"line": node.lineno - 1, "character": node.col_offset},
            "end": {"line": node.end_lineno - 1, "character": node.end_col_offset},
        }
    return {
        "contents": {"kind": kind, "value": "".join(signature_doc)},
        "range": show_range,
    }
