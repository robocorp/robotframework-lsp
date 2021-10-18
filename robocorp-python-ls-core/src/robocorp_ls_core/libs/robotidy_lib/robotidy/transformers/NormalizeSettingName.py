from robot.api.parsing import ModelTransformer, Token
from robot.utils.normalizing import normalize_whitespace

from robotidy.decorators import check_start_end_line


class NormalizeSettingName(ModelTransformer):
    """
    Normalize setting name.
    Ensure that setting names are title case without leading or trailing whitespace. For example from:

        *** Settings ***
        library    library.py
        test template    Template
        FORCE taGS    tag1

        *** Keywords ***
        Keyword
            [arguments]    ${arg}
            [ SETUP]   Setup Keyword

    To:

        *** Settings ***
        Library    library.py
        Test Template    Template
        Force Tags    tag1

        *** Keywords ***
        Keyword
            [Arguments]    ${arg}
            [Setup]   Setup Keyword

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/NormalizeSettingName.html for more examples.
    """

    @check_start_end_line
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
