import threading
import logging
from typing import (
    Any,
    Callable,
    Optional,
)
import itertools
from functools import partial

log = logging.getLogger(__name__)

DEBUG = False

_next_id = partial(next, itertools.count(0))


class _TkHandler:
    def __init__(self):
        self._current_thread = threading.current_thread()
        self._roots = []
        # Add the default one (to interact with the loop).
        self.add_rect(0, 0, 0, 0)

    def set_rects(self, rects):
        if DEBUG:
            print(f"--- Settings {len(rects)} rects (id: {_next_id()})")
        assert self._current_thread == threading.current_thread()

        reuse_index = 1

        for rect in rects:
            if DEBUG:
                print(rect)
            left, top, right, bottom = rect

            if reuse_index < len(self._roots):
                canvas = self._roots[reuse_index]
                self.set_canvas_geometry(canvas, left, right, top, bottom)
            else:
                self.add_rect(left, right, top, bottom)

            reuse_index += 1

        while len(rects) + 1 < len(self._roots):
            if DEBUG:
                print("Destroy unused")
            self._roots.pop(-1).destroy()

        assert len(self._roots) - 1 == len(rects)

    def _create_canvas(self):
        import tkinter as tk

        root = tk.Tk()
        root.title("Inspect picker root")
        root.overrideredirect(True)  # Remove window decorations
        root.attributes("-alpha", 0.4)  # Set window transparency (0.0 to 1.0)
        root.geometry("0x0+0+0")
        root.attributes("-topmost", 1)

        from tkinter.constants import SOLID

        canvas = tk.Canvas(
            root,
            bg="red",
            relief=SOLID,
            borderwidth=4,
            border=2,
        )

        canvas.pack(fill=tk.BOTH, expand=True)
        self._roots.append(root)
        return root

    def add_rect(self, left, right, top, bottom):
        assert self._current_thread == threading.current_thread()
        canvas = self._create_canvas()
        self.set_canvas_geometry(canvas, left, right, top, bottom)

    def set_canvas_geometry(self, canvas, left, right, top, bottom):
        x = left
        w = right - x

        y = top
        h = bottom - y

        assert w >= 0, f"Found w: {w}"
        assert h >= 0, f"Found h: {h}"

        canvas.geometry(f"{w}x{h}+{x}+{y}")

    def __len__(self):
        assert self._current_thread == threading.current_thread()
        return len(self._roots) - 1  # The default one doesn't count

    @property
    def _default_root(self):
        try:
            return self._roots[0]
        except IndexError:
            return None

    def loop(self, on_loop_poll_callback: Optional[Callable[[], Any]]):
        assert self._current_thread == threading.current_thread()

        poll_5_times_per_second = int(1 / 5.0 * 1000)

        if on_loop_poll_callback is not None:

            def check_action():
                # Keep calling itself
                on_loop_poll_callback()
                default_root = self._default_root
                if default_root is not None:
                    default_root.after(poll_5_times_per_second, check_action)

            default_root = self._default_root
            if default_root is not None:
                default_root.after(poll_5_times_per_second, check_action)

        default_root = self._default_root
        if default_root is not None:
            default_root.mainloop()

    def quit(self):
        assert self._current_thread == threading.current_thread()
        self._default_root.quit()

    def destroy_tk_handler(self):
        assert self._current_thread == threading.current_thread()
        for el in self._roots:
            el.destroy()
        del self._roots[:]

    def after(self, timeout, callback):
        # Can be called from any thread
        self._default_root.after(timeout, callback)


class TkHandlerThread(threading.Thread):
    """
    This is a thread-safe facade to use _TkHandler.

    The way it works is that this thread must be started and all the methods
    will actually add the actual action to a queue and then they'll return
    promptly (and later the thread should fetch the item from the queue
    and actually perform the needed operation on tk).
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.RLock()
        import queue

        self._queue: "queue.Queue[Callable[[], None]]" = queue.Queue()
        self._tk_handler: Optional[_TkHandler] = None
        self._quit_queue_loop = threading.Event()

    def run(self):
        while not self._quit_queue_loop.is_set():
            cmd = self._queue.get()
            if cmd is None:
                self._quit_queue_loop.set()
                return
            try:
                cmd()
            except Exception:
                import traceback

                traceback.print_exc()

    def dispose(self):
        self.quitloop()
        self.destroy_tk_handler()
        self._queue.put_nowait(None)  # Finishes the thread.

    def destroy_tk_handler(self):
        def destroy_tk_handler():
            with self._lock:
                if self._tk_handler is None:
                    return
                self._tk_handler.destroy_tk_handler()
                self._tk_handler = None

        self._queue.put_nowait(destroy_tk_handler)

    def add_rect(self, left, right, top, bottom):
        def add_rect():
            tk_handler = self._tk_handler
            if tk_handler is not None:
                self._tk_handler.add_rect(left, right, top, bottom)

        self._queue.put_nowait(add_rect)

    def set_rects(self, rects) -> threading.Event:
        """
        Returns:
            An event called after the rects were actually updated.
        """
        ev = threading.Event()

        def set_rects():
            try:
                tk_handler = self._tk_handler
                if tk_handler is not None:
                    tk_handler.set_rects(rects)
            finally:
                ev.set()

        self._queue.put_nowait(set_rects)
        return ev

    def loop(self):
        def loop():
            tk_handler = self._tk_handler
            if tk_handler is not None:

                def on_loop_poll_callback():
                    # This will be continually called in the tk loop.
                    # We use it to check whether something was added
                    # to the queue (so that the user can quit the
                    # loop for instance).
                    import queue

                    try:
                        cmd = self._queue.get_nowait()
                    except queue.Empty:
                        return

                    if cmd is None:
                        self._quit_queue_loop.set()
                        return

                    try:
                        cmd()
                    except Exception:
                        import traceback

                        traceback.print_exc()

                self._tk_handler.loop(on_loop_poll_callback)

        self._queue.put_nowait(loop)

    def create(self):
        def create():
            with self._lock:
                if self._tk_handler is not None:
                    self._tk_handler.destroy_tk_handler()
                    self._tk_handler = None
                self._tk_handler = _TkHandler()

        self._queue.put_nowait(create)

    def quitloop(self):
        def quitloop():
            with self._lock:
                tk_handler = self._tk_handler
                if tk_handler is not None:
                    tk_handler.quit()

        self._queue.put_nowait(quitloop)
