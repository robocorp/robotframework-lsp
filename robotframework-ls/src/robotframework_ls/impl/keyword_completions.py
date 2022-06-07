from typing import List

from robocorp_ls_core.protocols import check_implements
from robocorp_ls_core.robotframework_log import get_logger
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IKeywordFound,
    IKeywordCollector,
    AbstractKeywordCollector,
    KeywordUsageInfo,
)
from robocorp_ls_core.lsp import (
    TextEditTypedDict,
    CompletionItemTypedDict,
    InsertTextFormat,
)


log = get_logger(__name__)


class _Collector(AbstractKeywordCollector):
    def __init__(
        self, completion_context: ICompletionContext, keyword_usage: KeywordUsageInfo
    ):
        from robotframework_ls.impl.string_matcher import RobotStringMatcher
        from robotframework_ls.impl.string_matcher import (
            build_matchers_with_resource_or_library_scope,
        )
        from robotframework_ls.robot_config import create_convert_keyword_format_func
        from robot.api import Token
        from robotframework_ls.impl.robot_lsp_constants import (
            OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR,
        )

        token_str = keyword_usage.token.value

        self.completion_items: List[CompletionItemTypedDict] = []
        self.completion_context = completion_context
        self.selection = completion_context.sel
        self.token = keyword_usage.token

        self._add_arguments = True
        if keyword_usage.node.type in (Token.TEMPLATE, Token.TEST_TEMPLATE):
            # i.e.: In templates the arguments are added in the test.
            self._add_arguments = False
        else:
            # i.e.: if we have arguments already don't add arguments again.
            for t in keyword_usage.node.tokens:
                if t.type == t.ARGUMENT and t.value:
                    self._add_arguments = False
                    break

        config = completion_context.config
        self._arguments_separator = "    "
        if config:
            self._arguments_separator = config.get_setting(
                OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR, str, "    "
            ).replace(r"\t", "\t")
        self._matcher = RobotStringMatcher(token_str)
        self._scope_matchers = build_matchers_with_resource_or_library_scope(token_str)
        config = completion_context.config

        self._convert_keyword_format = create_convert_keyword_format_func(config)

    def accepts(self, keyword_name: str) -> bool:
        if self._matcher.accepts_keyword_name(keyword_name):
            return True
        for matcher in self._scope_matchers:
            if matcher.accepts_keyword_name(keyword_name):
                return True
        return False

    def _create_completion_item_from_keyword(
        self, keyword_found: IKeywordFound, selection, token, col_delta=0
    ) -> CompletionItemTypedDict:
        from robotframework_ls.impl.protocols import IKeywordArg

        label = keyword_found.keyword_name

        if keyword_found.library_name:
            # If we found the keyword in a library, convert its format depending on
            # the user configuration.
            label = self._convert_keyword_format(label)

        text = label

        if self._add_arguments:
            arg: IKeywordArg
            for i, arg in enumerate(keyword_found.keyword_args):
                if (
                    arg.is_keyword_arg
                    or arg.is_star_arg
                    or arg.default_value is not None
                ):
                    continue

                arg_name = arg.arg_name
                arg_name = (
                    arg_name.replace("$", "\\$").replace("{", "").replace("}", "")
                )

                text = f"{text}{self._arguments_separator}${{{i + 1}:{arg_name}}}"

        text_edit: TextEditTypedDict = {
            "range": {
                "start": {
                    "line": selection.line,
                    "character": token.col_offset + col_delta,
                },
                "end": {"line": selection.line, "character": token.end_col_offset},
            },
            "newText": text,
        }

        if keyword_found.library_name:
            label = f"{label} ({keyword_found.library_name})"

        elif keyword_found.resource_name:
            label = f"{label} ({keyword_found.resource_name})"

        return {
            "label": label,
            "kind": keyword_found.completion_item_kind,
            "textEdit": text_edit,
            "insertText": text_edit["newText"],
            "insertTextFormat": InsertTextFormat.Snippet,
        }

    def on_keyword(self, keyword_found):
        col_delta = 0
        if not self._matcher.accepts_keyword_name(keyword_found.keyword_name):
            for matcher in self._scope_matchers:
                if matcher.accepts_keyword(keyword_found):
                    # +1 for the dot
                    col_delta = len(matcher.resource_or_library_name) + 1
                    break
            else:
                return  # i.e.: don't add completion

        item = self._create_completion_item_from_keyword(
            keyword_found, self.selection, self.token, col_delta=col_delta
        )

        self.completion_context.assign_documentation_resolve(
            item, keyword_found.compute_docs_with_signature
        )

        self.completion_items.append(item)

    def __typecheckself__(self) -> None:
        _: IKeywordCollector = check_implements(self)


def complete(completion_context: ICompletionContext) -> List[CompletionItemTypedDict]:
    from robotframework_ls.impl.collect_keywords import collect_keywords
    from robotframework_ls.impl import ast_utils

    token_info = completion_context.get_current_token()
    if token_info is not None:
        keyword_usage = ast_utils.create_keyword_usage_info_from_token(
            token_info.stack, token_info.node, token_info.token
        )
        if keyword_usage is not None and not keyword_usage.token.value.strip().endswith(
            "}"
        ):
            collector = _Collector(completion_context, keyword_usage)
            collect_keywords(completion_context, collector)

            return collector.completion_items

    return []
