from typing import TypeVar
import sys

T = TypeVar("T")

if sys.version_info[:2] < (3, 8):
    # Hack so that we don't break the runtime on versions prior to Python 3.8.

    class TypedDict(object):
        pass


else:
    from typing import TypedDict


class ImageLocatorTypedDict(TypedDict):
    path_b64: str
    source_b64: str
    confidence: float
    type: str  # 'browser', 'image', ...


class BrowserLocatorTypedDict(TypedDict):
    strategy: str
    value: str
    source: str
    screenshot: str  # a.k.a: screenshot_as_base64
    type: str  # 'browser', 'image', ...


class BrowserLocatorValidationTypedDict(TypedDict):
    matches: int
    source: str
    screenshot: str
