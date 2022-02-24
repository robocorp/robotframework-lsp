from robocorp_ls_core.lsp import (
    HoverTypedDict,
    MarkupKind,
    SignatureHelp,
    SignatureInformation,
    MarkupContentTypedDict,
)
from typing import Optional


def hover(completion_context) -> Optional[HoverTypedDict]:
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

    if kind == MarkupKind.Markdown:
        signature_doc = ["**", escape(sig_help.name), "**"]
    else:
        signature_doc = [sig_help.name]

    if active_signature.parameters:
        signature_doc.append("(")
        for i, parameter in enumerate(active_signature.parameters):
            if i > 0:
                signature_doc.append(", ")

            if i == active_parameter:
                if kind == MarkupKind.Markdown:
                    signature_doc.append("*`")
                else:
                    signature_doc.append("`")

            signature_doc.append(escape(parameter.label))

            if i == active_parameter:
                if kind == MarkupKind.Markdown:
                    signature_doc.append("`*")
                else:
                    signature_doc.append("`")

        signature_doc.append(")")

    signature_doc.append("\n\n")
    signature_doc.append(documentation_markup["value"])

    return {
        "contents": {"kind": kind, "value": "".join(signature_doc)},
        "range": {
            "start": {"line": node.lineno - 1, "character": node.col_offset},
            "end": {"line": node.end_lineno - 1, "character": node.end_col_offset},
        },
    }

    return None
