class NoMatchingLocatorException(Exception):
    """Match for locator not found."""


class ContextNotAvailable(Exception):
    """The Java context has not been created yet."""


class LocatorNotProvidedException(Exception):
    """Locator not provided."""


class NoWindowSelected(Exception):
    """Window not selected yet."""
