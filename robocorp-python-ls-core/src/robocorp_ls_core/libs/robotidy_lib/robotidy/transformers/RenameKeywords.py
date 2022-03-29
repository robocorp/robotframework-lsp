import re
from typing import Optional
import string

from robot.api.parsing import ModelTransformer, Token, KeywordCall

from robotidy.decorators import check_start_end_line
from robotidy.exceptions import InvalidParameterValueError


class RenameKeywords(ModelTransformer):
    """
    Enforce keyword naming.

    Title Case is applied to keyword name and underscores are replaced by spaces.

    You can keep underscores if you set remove_underscores to False:

        robotidy --transform RenameKeywords -c RenameKeywords:remove_underscores=False .

    It is also possible to configure `replace_pattern` parameter to find and replace regex pattern. Use `replace_to`
    to set replacement value. This configuration (underscores are used instead of spaces):

        robotidy --transform RenameKeywords -c RenameKeywords:replace_pattern=^(?i)rename\s?me$:replace_to=New_Shining_Name .

    will transform following code:

        *** Keywords ***
        rename Me
           Keyword Call

    To:

        *** Keywords ***
        New Shining Name
            Keyword Call

    Use `ignore_library = True` parameter to control if the library name part (Library.Keyword) of keyword call
    should be renamed.

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/RenameKeywords.html for more examples.
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
        try:
            self.replace_pattern = re.compile(replace_pattern) if replace_pattern is not None else None
        except re.error as err:
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "replace_pattern",
                replace_pattern,
                f"It should be a valid regex expression. Regex error: '{err.msg}'",
            )
        self.replace_to = "" if replace_to is None else replace_to

    @check_start_end_line
    def rename_node(self, node, type_of_name):
        token = node.get_token(type_of_name)
        if not token or not token.value:
            return node
        values = []
        split_names = token.value.split(".")
        for index, value in enumerate(split_names, start=1):
            if self.ignore_library and index != len(split_names):
                values.append(value)
                continue
            if self.replace_pattern is not None:
                value = self.replace_pattern.sub(repl=self.replace_to, string=value)
            if self.remove_underscores and set(value) != {"_"}:
                value = re.sub("_+", " ", value)  # replace one or more _ with one space
            value = "".join([a if a.isupper() else b for a, b in zip(value, string.capwords(value.strip()))])
            values.append(value)
        token.value = ".".join(values)
        return node

    def visit_KeywordName(self, node):  # noqa
        return self.rename_node(node, Token.KEYWORD_NAME)

    def visit_KeywordCall(self, node):  # noqa
        return self.rename_node(node, Token.KEYWORD)
