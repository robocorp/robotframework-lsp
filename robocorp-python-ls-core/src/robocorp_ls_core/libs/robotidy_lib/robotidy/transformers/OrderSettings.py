from robot.api.parsing import ModelTransformer, EmptyLine, Comment, Token

from robotidy.decorators import check_start_end_line
from robotidy.exceptions import InvalidParameterValueError


class OrderSettings(ModelTransformer):
    """
    Order settings like [Arguments], [Setup], [Return] inside Keywords and Test Cases.

    Keyword settings [Documentation], [Tags], [Timeout], [Arguments] are put before keyword body and
    settings like [Teardown], [Return] are moved to the end of the keyword:

       *** Keywords ***
        Keyword
            [Teardown]  Keyword
            [Return]  ${value}
            [Arguments]  ${arg}
            [Documentation]  this is
            ...    doc
            [Tags]  sanity
            Pass

    To:

       *** Keywords ***
        Keyword
            [Documentation]  this is
            ...    doc
            [Tags]  sanity
            [Arguments]  ${arg}
            Pass
            [Teardown]  Keyword
            [Return]  ${value}

    Test case settings [Documentation], [Tags], [Template], [Timeout], [Setup] are put before test case body and
    [Teardown] is moved to the end of test case.

    Default order can be changed using following parameters:
      - ``keyword_before = documentation,tags,timeout,arguments``
      - ``keyword_after = teardown,return``
      - ``test_before = documentation,tags,template,timeout,setup
      - ``test_after = teardown

    Not all settings names need to be passed to given parameter. Missing setting names are not ordered. Example::

        robotidy --configure OrderSettings:keyword_before=:keyword_after=

    It will order only test cases because all setting names for keywords are missing.

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/OrderSettings.html for more examples.
    """

    def __init__(
        self,
        keyword_before: str = None,
        keyword_after: str = None,
        test_before: str = None,
        test_after: str = None,
    ):
        (
            self.keyword_before,
            self.keyword_after,
            self.test_before,
            self.test_after,
        ) = self.parse_order(keyword_before, keyword_after, test_before, test_after)
        self.keyword_settings = {*self.keyword_before, *self.keyword_after}
        self.test_settings = {*self.test_before, *self.test_after}

    def get_order(self, order, default, name_map):
        if order is None:
            return default
        if not order:
            return []
        parts = order.lower().split(",")
        try:
            return [name_map[part] for part in parts]
        except KeyError:
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "order",
                order,
                f"Custom order should be provided in comma separated list with valid setting names:\n{sorted(name_map.keys())}",
            )

    def parse_order(self, keyword_before, keyword_after, test_before, test_after):
        keyword_order_before = (
            Token.DOCUMENTATION,
            Token.TAGS,
            Token.TIMEOUT,
            Token.ARGUMENTS,
        )
        keyword_order_after = (
            Token.TEARDOWN,
            Token.RETURN,
        )
        testcase_order_before = (
            Token.DOCUMENTATION,
            Token.TAGS,
            Token.TEMPLATE,
            Token.TIMEOUT,
            Token.SETUP,
        )
        testcase_order_after = (Token.TEARDOWN,)
        keyword_map = {
            "documentation": Token.DOCUMENTATION,
            "tags": Token.TAGS,
            "timeout": Token.TIMEOUT,
            "arguments": Token.ARGUMENTS,
            "return": Token.RETURN,
            "teardown": Token.TEARDOWN,
        }
        test_map = {
            "documentation": Token.DOCUMENTATION,
            "tags": Token.TAGS,
            "timeout": Token.TIMEOUT,
            "template": Token.TEMPLATE,
            "setup": Token.SETUP,
            "teardown": Token.TEARDOWN,
        }
        return (
            self.get_order(keyword_before, keyword_order_before, keyword_map),
            self.get_order(keyword_after, keyword_order_after, keyword_map),
            self.get_order(test_before, testcase_order_before, test_map),
            self.get_order(test_after, testcase_order_after, test_map),
        )

    @check_start_end_line
    def visit_Keyword(self, node):  # noqa
        return self.order_settings(node, self.keyword_settings, self.keyword_before, self.keyword_after)

    @check_start_end_line
    def visit_TestCase(self, node):  # noqa
        return self.order_settings(node, self.test_settings, self.test_before, self.test_after)

    def order_settings(self, node, setting_types, before, after):
        if not node.body:
            return node
        settings = dict()
        not_settings, trailing_after = [], []
        after_seen = False
        # when after_seen is set to True then all statements go to trailing_after and last non data
        # will be appended after tokens defined in `after` set (like [Return])
        comment = []
        for child in node.body:
            if isinstance(child, Comment) and child.lineno == node.lineno:
                comment.append(child)
            elif getattr(child, "type", "invalid") in setting_types:
                after_seen = after_seen or child.type in after
                settings[child.type] = child
            elif after_seen:
                trailing_after.append(child)
            else:
                not_settings.append(child)
        # comments after last data statement are considered as comment outside body
        trailing_non_data = []
        while trailing_after and isinstance(trailing_after[-1], (EmptyLine, Comment)):
            trailing_non_data.insert(0, trailing_after.pop())
        not_settings += trailing_after
        node.body = (
            comment
            + self.add_in_order(before, settings)
            + not_settings
            + self.add_in_order(after, settings)
            + trailing_non_data
        )
        return node

    @staticmethod
    def add_in_order(order, settings_in_node):
        return [settings_in_node[token_type] for token_type in order if token_type in settings_in_node]
