from robot.api.parsing import Token

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

    NormalizeTags will change the formatting of the tags by removing the duplicates, new lines and moving comments.
    If you want to preserved formatting set ``preserve_format``:

    ```
    robotidy --configure NormalizeTags:preserve_format=True test.robot
    ```

    The duplicates will not be removed with ``preserve_format`` set to ``True``.
    """

    CASE_FUNCTIONS = {
        "lowercase": str.lower,
        "uppercase": str.upper,
        "titlecase": str.title,
    }

    def __init__(
        self,
        case: str = "lowercase",
        normalize_case: bool = True,
        preserve_format: bool = False,
    ):
        super().__init__()
        self.case = case.lower()
        self.normalize_case = normalize_case
        self.preserve_format = preserve_format
        try:
            self.case_function = self.CASE_FUNCTIONS[self.case]
        except KeyError:
            raise InvalidParameterValueError(
                self.__class__.__name__,
                "case",
                case,
                "Supported cases: lowercase, uppercase, titlecase.",
            )

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        return self.generic_visit(node)

    def visit_Tags(self, node):  # noqa
        return self.normalize_tags(node, indent=True)

    def visit_DefaultTags(self, node):  # noqa
        return self.normalize_tags(node)

    def visit_ForceTags(self, node):  # noqa
        return self.normalize_tags(node)

    def normalize_tags(self, node, indent=False):
        if self.disablers.is_node_disabled(node, full_match=False):
            return node
        if self.preserve_format:
            return self.normalize_tags_tokens_preserve_formatting(node)
        return self.normalize_tags_tokens_ignore_formatting(node, indent)

    def normalize_tags_tokens_preserve_formatting(self, node):
        if not self.normalize_case:
            return node
        for token in node.tokens:
            if token.type != Token.ARGUMENT:
                continue
            token.value = self.case_function(token.value)
        return node

    def normalize_tags_tokens_ignore_formatting(self, node, indent):
        separator = Token(Token.SEPARATOR, self.formatting_config.separator)
        setting_name = node.data_tokens[0]
        tags = [tag.value for tag in node.data_tokens[1:]]
        if self.normalize_case:
            tags = self.convert_case(tags)
        tags = self.remove_duplicates(tags)
        comments = node.get_tokens(Token.COMMENT)
        if indent:
            tokens = [
                Token(Token.SEPARATOR, self.formatting_config.indent),
                setting_name,
            ]
        else:
            tokens = [setting_name]
        for tag in tags:
            tokens.extend([separator, Token(Token.ARGUMENT, tag)])
        if comments:
            tokens.extend(self.join_tokens(comments))
        tokens.append(Token(Token.EOL))
        node.tokens = tuple(tokens)
        return node

    def convert_case(self, tags):
        return [self.case_function(item) for item in tags]

    @staticmethod
    def remove_duplicates(tags):
        return list(dict.fromkeys(tags))

    def join_tokens(self, tokens):
        joined_tokens = []
        separator = Token(Token.SEPARATOR, self.formatting_config.separator)
        for token in tokens:
            joined_tokens.extend([separator, token])
        return joined_tokens
