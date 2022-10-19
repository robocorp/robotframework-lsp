import re
import string
from typing import Optional

from robot.api.parsing import ModelTransformer, Token

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.transformers.run_keywords import get_run_keywords
from robotidy.utils import is_token_value_in_tokens, normalize_name, split_on_token_type, split_on_token_value


class RenameKeywords(ModelTransformer):
    """
    Enforce keyword naming.

    Title Case is applied to keyword name and underscores are replaced by spaces.

    You can keep underscores if you set remove_underscores to False:

    ```
    robotidy --transform RenameKeywords -c RenameKeywords:remove_underscores=False .
    ```

    It is also possible to configure `replace_pattern` parameter to find and replace regex pattern. Use `replace_to`
    to set replacement value. This configuration (underscores are used instead of spaces):

    ```
    robotidy --transform RenameKeywords -c RenameKeywords:replace_pattern=^(?i)rename\s?me$:replace_to=New_Shining_Name .
    ```

    will transform following code:

    ```robotframework
    *** Keywords ***
    rename Me
       Keyword Call
    ```

    To:

    ```robotframework
    *** Keywords ***
    New Shining Name
        Keyword Call
    ```

    Use `ignore_library = True` parameter to control if the library name part (Library.Keyword) of keyword call
    should be renamed.
    """

    ENABLED = False

    def __init__(
        self,
        replace_pattern: Optional[str] = None,
        replace_to: Optional[str] = None,
        remove_underscores: bool = True,
        ignore_library: bool = True,
    ):
        self.ignore_library = ignore_library
        self.remove_underscores = remove_underscores
        self.replace_pattern = self.parse_pattern(replace_pattern)
        self.replace_to = "" if replace_to is None else replace_to
        self.run_keywords = get_run_keywords()

    def parse_pattern(self, replace_pattern):
        if replace_pattern is None:
            return None
        try:
            return re.compile(replace_pattern)
        except re.error as err:
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "replace_pattern",
                replace_pattern,
                f"It should be a valid regex expression. Regex error: '{err.msg}'",
            )

    def get_run_keyword(self, kw_name):
        kw_norm = normalize_name(kw_name)
        return self.run_keywords.get(kw_norm, None)

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def rename_node(self, token, is_keyword_call):
        values = []
        split_names = token.value.split(".")
        for index, value in enumerate(split_names, start=1):
            if is_keyword_call and self.ignore_library and index != len(split_names):
                values.append(value)
                continue
            if self.replace_pattern is not None:
                value = self.replace_pattern.sub(repl=self.replace_to, string=value)
            if self.remove_underscores and set(value) != {"_"}:
                value = re.sub("_+", " ", value)  # replace one or more _ with one space
            value = value.strip()
            # capitalize first letter of every word, leave rest untouched
            value = "".join([a if a.isupper() else b for a, b in zip(value, string.capwords(value))])
            values.append(value)
        token.value = ".".join(values)

    @skip_if_disabled
    def visit_KeywordName(self, node):  # noqa
        name_token = node.get_token(Token.KEYWORD_NAME)
        if not name_token or not name_token.value:
            return node
        self.rename_node(name_token, is_keyword_call=False)
        return node

    @skip_if_disabled
    def visit_KeywordCall(self, node):  # noqa
        name_token = node.get_token(Token.KEYWORD)
        if not name_token or not name_token.value:
            return node
        # ignore assign, separators and comments
        _, tokens = split_on_token_type(node.data_tokens, Token.KEYWORD)
        self.parse_run_keyword(tokens)
        return node

    def parse_run_keyword(self, tokens):
        if not tokens:
            return
        self.rename_node(tokens[0], is_keyword_call=True)
        run_keyword = self.get_run_keyword(tokens[0].value)
        if not run_keyword:
            return
        tokens = tokens[run_keyword.resolve :]
        if run_keyword.branches:
            if "ELSE IF" in run_keyword.branches:
                while is_token_value_in_tokens("ELSE IF", tokens):
                    prefix, branch, tokens = split_on_token_value(tokens, "ELSE IF", 2)
                    self.parse_run_keyword(prefix)
            if "ELSE" in run_keyword.branches and is_token_value_in_tokens("ELSE", tokens):
                prefix, branch, tokens = split_on_token_value(tokens, "ELSE", 1)
                self.parse_run_keyword(prefix)
                self.parse_run_keyword(tokens)
                return
        elif run_keyword.split_on_and:
            return self.split_on_and(tokens)
        self.parse_run_keyword(tokens)

    def split_on_and(self, tokens):
        if not is_token_value_in_tokens("AND", tokens):
            for token in tokens:
                self.rename_node(token, is_keyword_call=True)
            return
        while is_token_value_in_tokens("AND", tokens):
            prefix, branch, tokens = split_on_token_value(tokens, "AND", 1)
            self.parse_run_keyword(prefix)
        self.parse_run_keyword(tokens)

    @skip_if_disabled
    def visit_SuiteSetup(self, node):  # noqa
        if node.errors:
            return node
        self.parse_run_keyword(node.data_tokens[1:])
        return node

    visit_SuiteTeardown = visit_TestSetup = visit_TestTeardown = visit_SuiteSetup

    @skip_if_disabled
    def visit_Setup(self, node):  # noqa
        if node.errors:
            return node
        self.parse_run_keyword(node.data_tokens[1:])
        return node

    visit_Teardown = visit_Setup
