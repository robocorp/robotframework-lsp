from robot.api.parsing import ModelTransformer, SectionHeader, Token

from robotidy.decorators import check_start_end_line


class NormalizeSectionHeaderName(ModelTransformer):
    """
    Normalize section headers names.
    Robot Framework is quite flexible with the section header naming. Following lines are equal:

        *setting
        *** SETTINGS
        *** SettingS ***

    This transformer normalizes naming to follow ``*** SectionName ***`` format (with plural variant):

        *** Settings ***
        *** Keywords ***
        *** Test Cases ***
        *** Variables ***
        *** Comments ***

    Optional data after section header (for example data driven column names) is preserved.
    It is possible to upper case section header names by passing ``uppercase=True`` parameter:

        *** SETTINGS ***

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/NormalizeSectionHeaderName.html for more examples.
    """

    def __init__(self, uppercase: bool = False):
        self.uppercase = uppercase

    @check_start_end_line
    def visit_SectionHeader(self, node):  # noqa
        if node.name and "task" in node.name:
            name = "*** Tasks ***"
        else:
            name = {
                Token.SETTING_HEADER: "*** Settings ***",
                Token.VARIABLE_HEADER: "*** Variables ***",
                Token.TESTCASE_HEADER: "*** Test Cases ***",
                Token.KEYWORD_HEADER: "*** Keywords ***",
                Token.COMMENT_HEADER: "*** Comments ***",
            }[node.type]
        if self.uppercase:
            name = name.upper()
        # we only modify header token value in order to preserver optional data driven testing column names
        node.data_tokens[0].value = name
        return node
