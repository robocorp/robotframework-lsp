from robot.api.parsing import DefaultTags, ForceTags, Tags, Token

from robotidy.disablers import skip_section_if_disabled
from robotidy.exceptions import InvalidParameterValueError
from robotidy.transformers import Transformer


class NormalizeTags(Transformer):
    """
    Normalize tag names by normalizing case and removing duplicates.
    Example usage:

    ```
    robotidy --transform NormalizeTags:case=lowercase test.robot
    ```

    Other supported cases: uppercase, title case. The default is lowercase.
    You can also run it to remove duplicates but preserve current case by setting ``normalize_case`` parameter to False:

    ```
    robotidy --transform NormalizeTags:normalize_case=False test.robot
    ```
    """

    CASE_FUNCTIONS = {
        "lowercase": str.lower,
        "uppercase": str.upper,
        "titlecase": str.title,
    }

    def __init__(self, case: str = "lowercase", normalize_case: bool = True):
        super().__init__()
        self.case = case.lower()
        self.normalize_case = normalize_case
        try:
            self.case_function = self.CASE_FUNCTIONS[self.case]
        except KeyError:
            raise InvalidParameterValueError(
                self.__class__.__name__, "case", case, "Supported cases: lowercase, uppercase, titlecase."
            )

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def visit_Tags(self, node):  # noqa
        return self.normalize_tags(node, Tags, indent=True)

    def visit_DefaultTags(self, node):  # noqa
        return self.normalize_tags(node, DefaultTags)

    def visit_ForceTags(self, node):  # noqa
        return self.normalize_tags(node, ForceTags)

    def normalize_tags(self, node, tag_class, indent=False):
        if self.disablers.is_node_disabled(node, full_match=False):
            return node
        tags = [tag.value for tag in node.data_tokens[1:]]
        if self.normalize_case:
            tags = self.convert_case(tags)
        tags = self.remove_duplicates(tags)
        comments = node.get_tokens(Token.COMMENT)
        if indent:
            tag_node = tag_class.from_params(
                tags,
                indent=self.formatting_config.indent,
                separator=self.formatting_config.separator,
            )
        else:
            tag_node = tag_class.from_params(tags, separator=self.formatting_config.separator)
        if comments:
            tag_node.tokens = tag_node.tokens[:-1] + tuple(self.join_tokens(comments)) + (tag_node.tokens[-1],)
        return tag_node

    def convert_case(self, tags):
        return [self.case_function(item) for item in tags]

    @staticmethod
    def remove_duplicates(tags):
        return list(dict.fromkeys(tags))

    def join_tokens(self, tokens):
        joined_tokens = []
        for token in tokens:
            joined_tokens.append(Token(Token.SEPARATOR, self.formatting_config.separator))
            joined_tokens.append(token)
        return joined_tokens
