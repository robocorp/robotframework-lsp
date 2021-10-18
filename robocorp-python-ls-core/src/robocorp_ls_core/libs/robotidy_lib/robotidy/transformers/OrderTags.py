from robot.api.parsing import ModelTransformer, Tags, Token, DefaultTags, ForceTags


class OrderTags(ModelTransformer):
    """
    Order tags.

    Tags are ordered in lexicographic order like this:

        *** Test Cases ***
        Tags Upper Lower
            [Tags]    ba    Ab    Bb    Ca    Cb    aa
            My Keyword

        *** Keywords ***
        My Keyword
            [Tags]    ba    Ab    Bb    Ca    Cb    aa
            No Operation

    To:

        *** Test Cases ***
        Tags Upper Lower
            [Tags]    aa    Ab    ba    Bb    Ca    Cb
            My Keyword

        *** Keywords ***
        My Keyword
            [Tags]    aa    Ab    ba    Bb    Ca    Cb
            No Operation

    Default order can be changed using following parameters:
      - ``case_sensitive = False``
      - ``reverse = False``

    See https://robotidy.readthedocs.io/en/latest/transformers/OrderTags.html for more examples.
    """

    ENABLED = False

    def __init__(
        self,
        case_sensitive: bool = False,
        reverse: bool = False,
        default_tags: bool = True,
        force_tags: bool = True,
    ):
        self.key = self.get_key(case_sensitive)
        self.reverse = reverse
        self.default_tags = default_tags
        self.force_tags = force_tags

    def visit_Tags(self, node):  # noqa
        return self.order_tags(node, Tags, indent=True)

    def visit_DefaultTags(self, node):  # noqa
        return self.order_tags(node, DefaultTags) if self.default_tags else node

    def visit_ForceTags(self, node):  # noqa
        return self.order_tags(node, ForceTags) if self.force_tags else node

    def order_tags(self, node, tag_class, indent=False):
        ordered_tags = sorted(
            (tag.value for tag in node.data_tokens[1:]),
            key=self.key,
            reverse=self.reverse,
        )
        if len(ordered_tags) <= 1:
            return node
        comments = node.get_tokens(Token.COMMENT)
        if indent:
            tag_node = tag_class.from_params(
                ordered_tags,
                indent=self.formatting_config.separator,
                separator=self.formatting_config.separator,
            )
        else:
            tag_node = tag_class.from_params(ordered_tags, separator=self.formatting_config.separator)
        if comments:
            tag_node.tokens = tag_node.tokens[:-1] + tuple(self.join_tokens(comments)) + (tag_node.tokens[-1],)
        return tag_node

    def join_tokens(self, tokens):
        joined_tokens = []
        for token in tokens:
            joined_tokens.append(Token(Token.SEPARATOR, self.formatting_config.separator))
            joined_tokens.append(token)
        return joined_tokens

    @staticmethod
    def get_key(case_sensitive):
        return str if case_sensitive else str.casefold
