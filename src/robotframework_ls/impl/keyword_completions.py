from robotframework_ls.robotframework_log import get_logger

log = get_logger(__name__)


class _Collector(object):
    def __init__(self, selection, token, matcher):
        self.matcher = matcher
        self.completion_items = []
        self.selection = selection
        self.token = token

    def accepts(self, keyword_name):
        return self.matcher.accepts(keyword_name)

    def _create_completion_item_from_keyword(self, keyword_found, selection, token):
        """
        :param IKeywordFound keyword_found:
        :param selection:
        :param token:
        """
        from robotframework_ls.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robotframework_ls.lsp import MarkupKind

        label = keyword_found.keyword_name
        text = label

        for i, arg in enumerate(keyword_found.keyword_args):
            text += "    ${%s:%s}" % (i + 1, arg)

        text_edit = TextEdit(
            Range(
                start=Position(selection.line, token.col_offset),
                end=Position(selection.line, token.end_col_offset),
            ),
            text,
        )

        # text_edit = None
        return CompletionItem(
            keyword_found.keyword_name,
            kind=keyword_found.completion_item_kind,
            text_edit=text_edit,
            documentation=keyword_found.docs,
            insertTextFormat=InsertTextFormat.Snippet,
            documentationFormat=(
                MarkupKind.Markdown
                if keyword_found.docs_format == "markdown"
                else MarkupKind.PlainText
            ),
        ).to_dict()

    def on_keyword(self, keyword_found):
        item = self._create_completion_item_from_keyword(
            keyword_found, self.selection, self.token
        )

        self.completion_items.append(item)


def complete(completion_context):
    """
    :param CompletionContext completion_context:
    """
    from robotframework_ls.impl.string_matcher import RobotStringMatcher
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None and ast_utils.is_keyword_name_location(
        token_info.node, token_info.token
    ):
        token = token_info.token
        collector = _Collector(
            completion_context.sel, token, RobotStringMatcher(token.value)
        )
        collect_keywords(completion_context, collector)

        return collector.completion_items

    return []
