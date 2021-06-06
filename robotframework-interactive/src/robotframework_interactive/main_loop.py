from typing import Optional, Callable


class MainLoopCallbackHolder:
    ON_MAIN_LOOP: Optional[Callable[[], None]] = None


def interpreter_main_loop():
    on_main_loop = MainLoopCallbackHolder.ON_MAIN_LOOP
    assert on_main_loop
    on_main_loop()  # pylint: disable=not-callable
