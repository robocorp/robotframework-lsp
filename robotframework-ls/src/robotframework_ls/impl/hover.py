from robocorp_ls_core.lsp import (
    HoverTypedDict,
    MarkupKind,
    SignatureHelp,
    SignatureInformation,
)
from typing import Optional


def hover(completion_context) -> Optional[HoverTypedDict]:
    from robotframework_ls.impl.signature_help import signature_help_internal
    from robocorp_ls_core.lsp import MarkupContent

    sig_help_and_node = signature_help_internal(completion_context)
    if sig_help_and_node is None:
        return None

    sig_help: SignatureHelp = sig_help_and_node[0]
    node = sig_help_and_node[1]
    signatures = sig_help.signatures
    if not signatures:
        return None
    try:
        active_signature: SignatureInformation = signatures[sig_help.activeSignature]
    except IndexError:
        active_signature = signatures[0]

    documentation_markup_or_str = active_signature.documentation

    if isinstance(documentation_markup_or_str, MarkupContent):
        kind = documentation_markup_or_str.kind
        documentation = documentation_markup_or_str.value

    elif isinstance(documentation_markup_or_str, str):
        kind = MarkupKind.PlainText
        documentation = documentation_markup_or_str

    else:
        kind = MarkupKind.PlainText
        documentation = str(documentation_markup_or_str)

    return {
        "contents": {"kind": kind, "value": documentation},
        "range": {
            "start": {"line": node.lineno - 1, "character": node.col_offset},
            "end": {"line": node.end_lineno - 1, "character": node.end_col_offset},
        },
    }

    return None
