from robot.api.parsing import Comment, CommentSection, EmptyLine

from robotidy.disablers import skip_section_if_disabled
from robotidy.transformers import Transformer


class DiscardEmptySections(Transformer):
    """
    Remove empty sections.
    Sections are considered empty if there are only empty lines inside.
    You can remove sections with only comments by setting ``allow_only_comments`` parameter to False:

    ```robotframework
    *** Variables ***
    # this section will be removed with ``alow_only_comments`` parameter set to False
    ```
    """

    def __init__(self, allow_only_comments: bool = True):
        super().__init__()
        # If False then sections with only with comments are considered to be empty
        self.allow_only_comments = allow_only_comments

    @skip_section_if_disabled
    def visit_Section(self, node):  # noqa
        anything_but = (
            EmptyLine if self.allow_only_comments or isinstance(node, CommentSection) else (Comment, EmptyLine)
        )
        if all(isinstance(child, anything_but) for child in node.body):
            return None
        return node
