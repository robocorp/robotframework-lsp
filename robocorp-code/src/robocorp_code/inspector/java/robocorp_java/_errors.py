class NoMatchingLocatorException(Exception):
    """Match for locator not found."""


class ContextNotAvailable(Exception):
    """The Java context has not been created yet."""
