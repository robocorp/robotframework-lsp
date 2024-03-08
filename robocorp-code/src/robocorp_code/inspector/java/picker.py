import math
import threading
import time
from typing import Callable, List, Optional, Tuple

from robocorp_code.inspector.java.highlighter import TkHandlerThread
from robocorp_ls_core.robotframework_log import ILog

from robocorp_code.inspector.java.java_inspector import RESOLUTION_PIXEL_RATIO


class CursorPos:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def as_tuple(self):
        return self.x, self.y

    def distance_to(self, cursor: "CursorPos"):
        dx = self.x - cursor.x
        dy = self.y - cursor.y
        distance = math.sqrt(dx**2 + dy**2)
        return distance

    def consider_same_as(self, cursor: Optional["CursorPos"]):
        if cursor is None:
            return False
        return self.distance_to(cursor) <= 3

    def __str__(self):
        return f"CursorPos({self.x}, {self.y})"

    __repr__ = __str__


class CursorListenerThread(threading.Thread):
    def __init__(
        self,
        log: ILog,
        tk_handler_thread: TkHandlerThread,
        # tree_geometries = [ (node_index, (left, top, right, bottom) ) ]
        tree_geometries: List[Tuple[int, Tuple]],
        # on_pick = func( (node_index, (left, top, right, bottom) ) )
        on_pick: Callable,
    ) -> None:
        threading.Thread.__init__(self)

        self.log = log
        self._stop_event = threading.Event()
        self._tk_handler_thread = tk_handler_thread
        self._tree_geometries = tree_geometries
        self._on_pick = on_pick

        self._element_hit: Optional[Tuple[int, Tuple]] = None

    def run(self) -> None:
        try:
            self._highlighter_start()
            self._run()
        except Exception:
            import traceback

            traceback.print_exc()

    def _run(self) -> None:
        from robocorp_code.inspector.windows.robocorp_windows._vendored.uiautomation.uiautomation import (
            GetCursorPos,
            UIAutomationInitializerInThread,
        )

        with UIAutomationInitializerInThread(debug=True):
            while True:
                if self._stop_event.wait(0.2):
                    return

                cursor_pos = CursorPos(*GetCursorPos())
                # self.log.info("@@@@@ Cursor position:", cursor_pos)

                time.sleep(0.1)
                if not self._is_cursor_still_on_element(cursor_pos.x, cursor_pos.y):
                    self._find_element_based_on_cursor(cursor_pos.x, cursor_pos.y)
                    time.sleep(0.1)
                    if self._element_hit:
                        _, geometry = self._element_hit
                        # draw the highlight
                        self._highlighter_draw(rects=[geometry])
                        self.log.info(
                            f"@@@@@@ Calling on pick with:   {self._element_hit}"
                        )
                        self._on_pick(self._element_hit)
                else:
                    time.sleep(0.5)
                    self._highlighter_clear()
                time.sleep(0.1)

    def _highlighter_start(self):
        self._highlighter_clear()
        self._highlighter_stop()
        # recreate the TK thread
        self._tk_handler_thread.create()
        self._tk_handler_thread.loop()

    def _highlighter_stop(self):
        # kill the TK thread
        self._tk_handler_thread.quitloop()
        self._tk_handler_thread.destroy_tk_handler()

    def _highlighter_clear(self):
        self._tk_handler_thread.set_rects(rects=[])

    def _highlighter_draw(self, rects: List[Tuple]):
        self._tk_handler_thread.set_rects(rects=rects)

    def _find_element_based_on_cursor(self, x: int, y: int):
        for elem in reversed(self._tree_geometries):
            _, geometry = elem
            left, top, right, bottom = geometry
            if x >= left and x <= right and y >= top and y <= bottom:
                self._element_hit = elem
                return
        self._element_hit = None

    def _is_cursor_still_on_element(self, x: int, y: int):
        if self._element_hit is None:
            return False
        _, geometry = self._element_hit
        left, top, right, bottom = geometry
        if x >= left and x <= right and y >= top and y <= bottom:
            return True
        return False

    def stop(self):
        self._highlighter_clear()
        self._stop_event.set()
