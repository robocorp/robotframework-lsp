from typing import List, Container

from robocorp_ls_core.protocols import check_implements, IDocumentSelection
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
    CompletionItemTag,
)
from robotframework_ls.impl.text_utilities import normalize_robot_name


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
            OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME,
            OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME_IGNORE,
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
        self._prefix_with_import_name = False
        self._prefix_with_import_name_ignore: Container[str] = ()
        if config:
            self._arguments_separator = config.get_setting(
                OPTION_ROBOT_COMPLETION_KEYWORDS_ARGUMENTS_SEPARATOR, str, "    "
            ).replace(r"\t", "\t")

            self._prefix_with_import_name = config.get_setting(
                OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME, bool, False
            )

            self._prefix_with_import_name_ignore = set(
                normalize_robot_name(x)
                for x in config.get_setting(
                    OPTION_ROBOT_COMPLETIONS_KEYWORDS_PREFIX_IMPORT_NAME_IGNORE,
                    (list, tuple),
                    (),
                )
            )

        self._is_dotted_keyword_name = "." in token_str
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
        self,
        keyword_found: IKeywordFound,
        selection: IDocumentSelection,
        token,
        prefix_with_import_name: bool,
        col_delta: int = 0,
    ) -> CompletionItemTypedDict:
        from robotframework_ls.impl.protocols import IKeywordArg
        from robotframework_ls.impl.variable_resolve import iter_robot_variable_matches

        label = keyword_found.keyword_name

        if keyword_found.library_name:
            # If we found the keyword in a library, convert its format depending on
            # the user configuration.
            label = self._convert_keyword_format(label)

        text = label
        replace_idx = 0
        if "{" in text:
            new_text = []
            var_match = None
            for var_match, _ in iter_robot_variable_matches(text):
                new_text.append(var_match.before)
                if var_match.name:
                    replace_idx += 1
                    new_text.append(f"${{{replace_idx}:\\${var_match.base}}}")

            if var_match is not None:
                new_text.append(var_match.after)
                text = "".join(new_text)

        if self._add_arguments:
            arg: IKeywordArg
            for _i, arg in enumerate(keyword_found.keyword_args):
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

                replace_idx += 1
                text = f"{text}{self._arguments_separator}${{{replace_idx}:{arg_name}}}"

        if keyword_found.library_name:
            use_libname = keyword_found.library_alias
            if not use_libname:
                use_libname = keyword_found.library_name
            if prefix_with_import_name:
                if self._is_dotted_keyword_name:
                    # Note: the label must also be updated because we're
                    # going to replace from the start, so, the start
                    # from the label must also match as it'll be used
                    # in the filtering.
                    text = f"{use_libname}.{text}"
                    label = f"{use_libname}.{label}"
                else:
                    if (
                        normalize_robot_name(use_libname)
                        in self._prefix_with_import_name_ignore
                    ):
                        # Don't change the text...
                        label = f"{label} ({use_libname})"
                    else:
                        text = f"{use_libname}.{text}"
                        label = f"{label} ({use_libname})"
            else:
                label = f"{label} ({use_libname})"

        elif keyword_found.resource_name:
            if prefix_with_import_name:
                if self._is_dotted_keyword_name:
                    text = f"{keyword_found.resource_name}.{text}"
                    label = f"{keyword_found.resource_name}.{label}"
                else:
                    if (
                        normalize_robot_name(keyword_found.resource_name)
                        in self._prefix_with_import_name_ignore
                    ):
                        # Don't change the text...
                        label = f"{label} ({keyword_found.resource_name})"
                    else:
                        text = f"{keyword_found.resource_name}.{text}"
                        label = f"{label} ({keyword_found.resource_name})"
            else:
                label = f"{label} ({keyword_found.resource_name})"

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

        ret: CompletionItemTypedDict = {
            "label": label,
            "kind": keyword_found.completion_item_kind,
            "textEdit": text_edit,
            "insertText": text_edit["newText"],
            "insertTextFormat": InsertTextFormat.Snippet,
        }
        if keyword_found.is_deprecated():
            ret["tags"] = [CompletionItemTag.Deprecated]
        return ret

    def on_keyword(self, keyword_found: IKeywordFound):
        col_delta = 0

        if not self._matcher.accepts_keyword_name(keyword_found.keyword_name):
            for matcher in self._scope_matchers:
                if matcher.accepts_keyword(keyword_found):
                    # +1 for the dot
                    col_delta = len(matcher.resource_or_library_name) + 1
                    break
            else:
                return  # i.e.: don't add completion

        prefix_with_import_name = self._prefix_with_import_name

        if prefix_with_import_name:
            if keyword_found.keyword_ast is not None:
                keyword_completion_context = keyword_found.completion_context
                if keyword_completion_context is not None:
                    if (
                        keyword_completion_context.doc.uri
                        == self.completion_context.doc.uri
                    ):
                        prefix_with_import_name = False

        if prefix_with_import_name:
            # If we're going to prefix with the module, replace
            # it completely and not from the dot.
            col_delta = 0

        item = self._create_completion_item_from_keyword(
            keyword_found,
            self.selection,
            self.token,
            prefix_with_import_name,
            col_delta=col_delta,
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
