from robot.api.parsing import Token

from robotidy.disablers import skip_section_if_disabled
from robotidy.transformers import Transformer


class NormalizeSectionHeaderName(Transformer):
    """
    Normalize section headers names.
    Robot Framework is quite flexible with the section header naming. Following lines are equal:

    ```robotframework
    *setting
    *** SETTINGS
    *** SettingS ***
    ```

    This transformer normalizes naming to follow ``*** SectionName ***`` format (with plural variant):

    ```robotframework
    *** Settings ***
    *** Keywords ***
    *** Test Cases ***
    *** Variables ***
    *** Comments ***
    ```

    Optional data after section header (for example data driven column names) is preserved.
    It is possible to upper case section header names by passing ``uppercase=True`` parameter:

    ```robotframework
    *** SETTINGS ***
    ```
    """

    def __init__(self, uppercase: bool = False):
        super().__init__()
        self.uppercase = uppercase

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def visit_SectionHeader(self, node):  # noqa
        if node.name and "task" in node.name.lower():
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
