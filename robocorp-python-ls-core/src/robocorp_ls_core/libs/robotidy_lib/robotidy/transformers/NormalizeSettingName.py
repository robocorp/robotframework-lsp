from robot.api.parsing import Token
from robot.utils.normalizing import normalize_whitespace

from robotidy.disablers import skip_if_disabled, skip_section_if_disabled
from robotidy.transformers import Transformer


class NormalizeSettingName(Transformer):
    """
    Normalize setting name.
    Ensure that setting names are title case without leading or trailing whitespace. For example from:

    ```robotframework
    *** Settings ***
    library    library.py
    test template    Template
    FORCE taGS    tag1

    *** Keywords ***
    Keyword
        [arguments]    ${arg}
        [ DOCUMENTATION]   Setup Keyword
    ```

    To:

    ```robotframework
    *** Settings ***
    Library    library.py
    Test Template    Template
    Force Tags    tag1

    *** Keywords ***
    Keyword
        [Arguments]    ${arg}
        [Documentation]   Setup Keyword
    ```
    """

    def __init__(self):
        super().__init__()  # workaround for our dynamically imported classes with args from cli/config

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    @skip_if_disabled
    def visit_Statement(self, node):  # noqa
        if node.type not in Token.SETTING_TOKENS:
            return node
        name = node.data_tokens[0].value
        if name.startswith("["):
            name = f"[{self.normalize_name(name[1:-1])}]"
        else:
            name = self.normalize_name(name)
        node.data_tokens[0].value = name
        return node

    @staticmethod
    def normalize_name(name):
        return normalize_whitespace(name).strip().title()
