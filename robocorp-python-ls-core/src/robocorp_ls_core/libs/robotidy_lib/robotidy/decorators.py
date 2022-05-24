import functools
import sys

import click

from robotidy.exceptions import (
    ImportTransformerError,
    InvalidParameterError,
    InvalidParameterFormatError,
    InvalidParameterValueError,
)


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
