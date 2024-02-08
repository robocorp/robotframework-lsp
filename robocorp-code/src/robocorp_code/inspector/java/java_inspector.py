from typing import List, TypedDict, cast

from JABWrapper.jab_wrapper import JavaWindow

JavaWindowInfoTypedDict = TypedDict(
    "JavaWindowInfoTypedDict",
    {
        # Same as JavaWindow
        "pid": int,
        "hwnd": int,
        "title": str,
    },
)


def to_window_info(java_window: JavaWindow) -> JavaWindowInfoTypedDict:
    ret = {}
    for dct_name in JavaWindowInfoTypedDict.__annotations__:
        ret[dct_name] = getattr(java_window, dct_name)
    return cast(JavaWindowInfoTypedDict, ret)


class JavaInspector:
    def __init__(self):
        from robocorp_code.inspector.java.robocorp_java._inspector import (
            ElementInspector,
        )

        self._inspector = ElementInspector()

    def list_windows(self) -> List[JavaWindowInfoTypedDict]:
        windows = self._inspector.list_windows()
        return [to_window_info(window) for window in windows]
