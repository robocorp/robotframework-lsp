from robocorp_ls_core.lsp import HoverTypedDict, MarkupKind
from robotframework_ls.impl.protocols import IKeywordFound
from typing import Optional


def hover(completion_context) -> Optional[HoverTypedDict]:
    current_keyword_definition_and_usage_info = (
        completion_context.get_current_keyword_definition_and_usage_info()
    )
    if current_keyword_definition_and_usage_info is not None:
        keyword_definition, usage_info = current_keyword_definition_and_usage_info

        keyword_found: IKeywordFound = keyword_definition.keyword_found

        documentation = keyword_found.docs
        kind = keyword_found.docs_format
        if kind not in (MarkupKind.Markdown, MarkupKind.PlainText):
            kind = MarkupKind.PlainText

        node = usage_info.node

        return {
            "contents": {"kind": kind, "value": documentation},
            "range": {
                "start": {"line": node.lineno - 1, "character": node.col_offset},
                "end": {"line": node.end_lineno - 1, "character": node.end_col_offset},
            },
        }

    return None
