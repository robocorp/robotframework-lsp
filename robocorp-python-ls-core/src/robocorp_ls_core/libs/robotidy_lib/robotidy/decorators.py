import sys
import functools

import click

from robotidy.utils import node_within_lines
from robotidy.exceptions import (
    InvalidParameterValueError,
    InvalidParameterError,
    InvalidParameterFormatError,
    ImportTransformerError,
)


def check_start_end_line(func):
    """
    Do not transform node if it's not within passed start_line and end_line.
    """

    @functools.wraps(func)
    def wrapper(self, node, *args):
        if not node:
            return node
        if not node_within_lines(
            node.lineno,
            node.end_lineno,
            self.formatting_config.start_line,
            self.formatting_config.end_line,
        ):
            return node
        return func(self, node, *args)

    return wrapper


def catch_exceptions(func):
    """
    Catch exceptions and print user friendly message for common issues
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not func:
            return functools.partial(catch_exceptions)
        try:
            return func(*args, **kwargs)
        except (
            InvalidParameterValueError,
            InvalidParameterError,
            InvalidParameterFormatError,
            ImportTransformerError,
        ) as err:
            print(f"Error: {err}")
            sys.exit(1)
        except (click.exceptions.ClickException, click.exceptions.Exit):
            raise
        except Exception as err:
            message = (
                "\nFatal exception occurred. You can create an issue at "
                "https://github.com/MarketSquare/robotframework-tidy/issues . Thanks!"
            )
            err.args = (err.args[0] + message,) + err.args[1:]
            raise err

    return wrapper
