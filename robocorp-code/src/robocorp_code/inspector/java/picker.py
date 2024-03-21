import math
import threading
import time
from typing import Callable, List, Optional, Tuple

from robocorp_code.inspector.java.highlighter import TkHandlerThread
from robocorp_ls_core.robotframework_log import ILog


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
        tk_handler_thread: Optional[TkHandlerThread],
        # tree_geometries = [ (node_index, (left, top, right, bottom), node ) ]
        tree_geometries: List[Tuple[int, Tuple, dict]],
        # on_pick = func( (node_index, (left, top, right, bottom), node ) )
        on_pick: Callable,
    ) -> None:
        threading.Thread.__init__(self)

        self.log = log
        self._stop_event = threading.Event()
        self._tk_handler_thread = tk_handler_thread
        self._tree_geometries = tree_geometries
        self._on_pick = on_pick

        # _element_hit = ( node_index, (left, top, right, bottom), node )
        self._element_hit: Optional[Tuple[int, Tuple, dict]] = None

    def run(self) -> None:
        try:
            self._highlighter_start()
            self._run()
        except Exception as e:
            self.log.exception("Exception raised while running:", e)

    def _run(self) -> None:
        from robocorp_code.inspector.windows.robocorp_windows._vendored.uiautomation.uiautomation import (
            GetCursorPos,
            UIAutomationInitializerInThread,
        )

        with UIAutomationInitializerInThread(debug=True):
            DEFAULT_TIME_FOR_HOVER: float = 2  # expressed in seconds
            time_spent_on_element: float = DEFAULT_TIME_FOR_HOVER

            while True:
                if self._stop_event.wait(0.2):
                    return

                cursor_pos = CursorPos(*GetCursorPos())

                if not self._is_cursor_still_on_element(cursor_pos.x, cursor_pos.y):
                    if time_spent_on_element <= 0:
                        self._highlighter_clear()
                        self._find_element_based_on_cursor(cursor_pos.x, cursor_pos.y)
                        time_spent_on_element = DEFAULT_TIME_FOR_HOVER

                        if self._element_hit:
                            _, geometry, _ = self._element_hit
                            # draw the highlight & send the element to middleware
                            self._highlighter_draw(rects=[geometry])
                            self.log.debug(
                                f"Java:: Picked element (on_pick callback): {self._element_hit}"
                            )
                            self._on_pick(self._element_hit)
                    else:
                        time_spent_on_element -= 0.2

    def _highlighter_start(self):
        self._highlighter_clear()
        self._highlighter_stop()
        # recreate the TK thread
        if self._tk_handler_thread:
            self._tk_handler_thread.create()
            self._tk_handler_thread.loop()

    def _highlighter_stop(self):
        # kill the TK thread
        if self._tk_handler_thread:
            self._tk_handler_thread.quitloop()
            self._tk_handler_thread.destroy_tk_handler()

    def _highlighter_clear(self):
        if self._tk_handler_thread:
            self._tk_handler_thread.set_rects(rects=[])

    def _highlighter_draw(self, rects: List[Tuple]):
        if self._tk_handler_thread:
            self._tk_handler_thread.set_rects(rects=rects)

    def _find_element_based_on_cursor(self, x: int, y: int):
        for elem in reversed(self._tree_geometries):
            _, geometry, _ = elem
            left, top, right, bottom = geometry
            if x >= left and x <= right and y >= top and y <= bottom:
                self._element_hit = elem
                return
        self._element_hit = None

    def _is_cursor_still_on_element(self, x: int, y: int):
        if self._element_hit is None:
            return False
        _, geometry, _ = self._element_hit
        left, top, right, bottom = geometry
        if x >= left and x <= right and y >= top and y <= bottom:
            return True
        return False

    def stop(self):
        self._highlighter_clear()
        self._stop_event.set()
