import ast

import click
from robot.api.parsing import ModelTransformer, Token

from robotidy.decorators import check_start_end_line


# TODO: preserve comments?
class RemoveEmptySettings(ModelTransformer):
    """
    Remove empty settings.

    You can configure which settings are affected by parameter ``work_mode``. Possible values:
        - overwrite_ok (default): does not remove settings that are overwriting suite settings (Test Setup,
          Test Teardown, Test Template, Test Timeout or Default Tags)
        - always : works on every settings

    Empty settings that are overwriting suite settings will be converted to be more explicit
    (given that there is related suite settings present)::

        No timeout
        [Documentation]    Empty timeout means no timeout even when Test Timeout has been used.
        [Timeout]

    To::

        No timeout
        [Documentation]    Disabling timeout with NONE works too and is more explicit.
        [Timeout]    NONE

    You can disable that behavior by changing ``more_explicit`` parameter value to ``False``.

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/RemoveEmptySettings.html for more examples.
    """

    def __init__(self, work_mode: str = "overwrite_ok", more_explicit: bool = True):
        if work_mode not in ("overwrite_ok", "always"):
            raise click.BadOptionUsage(
                option_name="transform",
                message=f"Invalid configurable value: {work_mode} for work_mode for RemoveEmptySettings transformer."
                f" Possible values:\n    overwrite_ok\n    always",
            )
        self.work_mode = work_mode
        self.more_explicit = more_explicit
        self.overwritten_settings = set()
        self.child_types = {
            Token.SETUP,
            Token.TEARDOWN,
            Token.TIMEOUT,
            Token.TEMPLATE,
            Token.TAGS,
        }

    @check_start_end_line
    def visit_Statement(self, node):  # noqa
        # when not setting type or setting type but not empty
        if node.type not in Token.SETTING_TOKENS or len(node.data_tokens) != 1:
            return node
        # when empty and not overwriting anything - remove
        if (
            node.type not in self.child_types
            or self.work_mode == "always"
            or node.type not in self.overwritten_settings
        ):
            return None
        if self.more_explicit:
            indent = node.tokens[0].value if node.tokens[0].type == Token.SEPARATOR else ""
            setting_token = node.data_tokens[0]
            node.tokens = [
                Token(Token.SEPARATOR, indent),
                setting_token,
                Token(Token.SEPARATOR, self.formatting_config.separator),
                Token(Token.ARGUMENT, "NONE"),
                Token(Token.EOL, "\n"),
            ]
        return node

    def visit_File(self, node):  # noqa
        if self.work_mode == "overwrite_ok":
            self.overwritten_settings = self.find_overwritten_settings(node)
        self.generic_visit(node)
        self.overwritten_settings = set()

    @staticmethod
    def find_overwritten_settings(node):
        auto_detector = FindSuiteSettings()
        auto_detector.visit(node)
        return auto_detector.suite_settings


class FindSuiteSettings(ast.NodeVisitor):
    def __init__(self):
        self.suite_settings = set()

    def check_setting(self, node, overwritten_type):
        if len(node.data_tokens) != 1:
            self.suite_settings.add(overwritten_type)

    def visit_TestSetup(self, node):  # noqa
        self.check_setting(node, Token.SETUP)

    def visit_TestTeardown(self, node):  # noqa
        self.check_setting(node, Token.TEARDOWN)

    def visit_TestTemplate(self, node):  # noqa
        self.check_setting(node, Token.TEMPLATE)

    def visit_TestTimeout(self, node):  # noqa
        self.check_setting(node, Token.TIMEOUT)

    def visit_DefaultTags(self, node):  # noqa
        self.check_setting(node, Token.TAGS)
