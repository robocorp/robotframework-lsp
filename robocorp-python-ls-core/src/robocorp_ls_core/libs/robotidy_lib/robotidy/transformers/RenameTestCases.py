import re
from typing import Optional

import click
from robot.api.parsing import ModelTransformer, Token

from robotidy.decorators import check_start_end_line


class RenameTestCases(ModelTransformer):
    r"""
    Enforce test case naming.

    Capitalize first letter of test case name, remove trailing dot and strip leading/trailing whitespace.

    It is also possible to configure `replace_pattern` parameter to find and replace regex pattern. Use `replace_to`
    to set replacement value. This configuration:

        robotidy --transform RenameTestCases -c RenameTestCases:replace_pattern=[A-Z]{3,}-\d{2,}:replace_to=foo

    will transform following code:

        *** Test Cases ***
        test ABC-123
            No Operation

    To:

        *** Test Cases ***
        Test foo
            No Operation

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/RenameTestCases.html for more examples.
    """
    ENABLED = False

    def __init__(self, replace_pattern: Optional[str] = None, replace_to: Optional[str] = None):
        try:
            self.replace_pattern = re.compile(replace_pattern) if replace_pattern is not None else None
        except re.error as err:
            raise click.BadOptionUsage(
                option_name="transform",
                message=f"Invalid configurable value: '{replace_pattern}' for replace_pattern in RenameTestCases"
                f" transformer. It should be a valid regex expression. Regex error: '{err.msg}'",
            )
        self.replace_to = "" if replace_to is None else replace_to

    @check_start_end_line
    def visit_TestCaseName(self, node):  # noqa
        token = node.get_token(Token.TESTCASE_NAME)
        if token.value:
            token.value = token.value[0].upper() + token.value[1:]
            if self.replace_pattern is not None:
                token.value = self.replace_pattern.sub(repl=self.replace_to, string=token.value)
            if token.value.endswith("."):
                token.value = token.value[:-1]
            token.value = token.value.strip()
        return node
