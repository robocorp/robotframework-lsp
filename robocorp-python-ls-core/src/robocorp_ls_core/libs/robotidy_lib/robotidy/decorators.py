import functools

from robotidy.utils import node_within_lines


def return_node_untouched(node):
    return node


def check_start_end_line(func):
    """
    Do not transform node if it's not within passed start_line and end_line.
    """

    @functools.wraps(func)
    def wrapper(self, node, *args):
        if not node:
            return return_node_untouched(node)
        if not node_within_lines(
            node.lineno,
            node.end_lineno,
            self.formatting_config.start_line,
            self.formatting_config.end_line,
        ):
            return return_node_untouched(node)
        return func(self, node, *args)

    return wrapper
