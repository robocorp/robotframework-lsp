import re
import string
from typing import Optional

from robot.api.parsing import Token
from robot.variables.search import VariableIterator

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.transformers import Transformer
from robotidy.transformers.run_keywords import get_run_keywords
from robotidy.utils import is_token_value_in_tokens, normalize_name, split_on_token_type, split_on_token_value


class RenameKeywords(Transformer):
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
        super().__init__()
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
        if self.replace_pattern is not None:
            new_value = self.rename_with_pattern(token.value, is_keyword_call=is_keyword_call)
        else:
            new_value = self.normalize_name(token.value, is_keyword_call=is_keyword_call)
        new_value = new_value.strip()
        if not new_value:  # do not allow renaming that removes keywords altogether
            return
        token.value = new_value

    def normalize_name(self, value, is_keyword_call):
        var_found = False
        parts = []
        remaining = ""
        for prefix, match, remaining in VariableIterator(value, ignore_errors=True):
            var_found = True
            # rename strips whitespace, so we need to preserve it if needed
            if not prefix.strip() and parts:
                parts.extend([" ", match])
            else:
                parts.extend([self.rename_part(prefix, is_keyword_call), match])
        if var_found:
            parts.append(self.rename_part(remaining, is_keyword_call))
            return "".join(parts).strip()
        return self.rename_part(value, is_keyword_call)

    def rename_part(self, part: str, is_keyword_call: bool):
        if is_keyword_call and self.ignore_library:
            lib_name, *kw_name = part.rsplit(".", maxsplit=1)
            if not kw_name:
                return self.remove_underscores_and_capitalize(part)
            return f"{lib_name}.{self.remove_underscores_and_capitalize(kw_name[0])}"
        return ".".join([self.remove_underscores_and_capitalize(name_part) for name_part in part.split(".")])

    def remove_underscores_and_capitalize(self, value: str):
        if self.remove_underscores:
            value = value.replace("_", " ")
            value = re.sub(r" +", " ", value)  # replace one or more spaces by one
        words = []
        split_words = value.split(" ")
        # capitalize first letter of every word, leave rest untouched
        for index, word in enumerate(split_words):
            if not word:
                if index in (0, len(split_words) - 1):  # leading and trailing whitespace
                    words.append("")
            else:
                words.append(word[0].upper() + word[1:])
        return " ".join(words)

    def rename_with_pattern(self, value: str, is_keyword_call: bool):
        lib_name = ""
        if is_keyword_call and "." in value:
            # rename only non lib part
            found_lib = -1
            for prefix, _, _ in VariableIterator(value):
                found_lib = prefix.find(".")
                break
            if found_lib != -1:
                lib_name = value[: found_lib + 1]
                value = value[found_lib + 1 :]
            else:
                lib_name, value = value.split(".", maxsplit=1)
                lib_name += "."
        if lib_name and not self.ignore_library:
            lib_name = self.remove_underscores_and_capitalize(lib_name)
        return lib_name + self.remove_underscores_and_capitalize(
            self.replace_pattern.sub(repl=self.replace_to, string=value)
        )

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
