from robot.api.parsing import ModelTransformer, EmptyLine, Comment, CommentSection
from robotidy.decorators import check_start_end_line


class DiscardEmptySections(ModelTransformer):
    """
    Remove empty sections.
    Sections are considered empty if there is no data or there are only comments inside (with the exception
    for ``*** Comments ***`` section).
    You can leave sections with only comments by setting ``allow_only_comments`` parameter to True::

        *** Variables ***
        # this section would be removed if not for ``alow_only_comments`` parameter

    Supports global formatting params: ``--startline`` and ``--endline``.

    See https://robotidy.readthedocs.io/en/latest/transformers/DiscardEmptySections.html for more examples.
    """

    def __init__(self, allow_only_comments: bool = False):
        # If True then sections only with comments are not is considered to be empty
        self.allow_only_comments = allow_only_comments

    @check_start_end_line
    def visit_Section(self, node):  # noqa
        anything_but = (
            EmptyLine if self.allow_only_comments or isinstance(node, CommentSection) else (Comment, EmptyLine)
        )
        if all(isinstance(child, anything_but) for child in node.body):
            return None
        return node
