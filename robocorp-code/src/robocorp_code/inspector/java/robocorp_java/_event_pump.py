import ctypes
import platform
import threading
import time
from concurrent import futures

from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


REMOVE_FROM_QUEUE = 0x0001


class EventPumpThread(threading.Thread):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        # Jab wrapper needs to be part of the thread that pumps the window events
        self._jab_wrapper: JavaAccessBridgeWrapper = None
        self._future: futures.Future = futures.Future()
        self._quit_event_loop = threading.Event()

    def _pump_background(self) -> bool:
        try:
            PeekMessage = ctypes.windll.user32.PeekMessageW  # type: ignore
            TranslateMessage = ctypes.windll.user32.TranslateMessage  # type: ignore
            DispatchMessage = ctypes.windll.user32.DispatchMessageW  # type: ignore

            message = ctypes.byref(ctypes.wintypes.MSG())
            # Nonblocking API to get windows window events from the queue.
            # https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-peekmessagea
            # Use non blocing API here so that the thread can quit.
            if PeekMessage(message, 0, 0, 0, REMOVE_FROM_QUEUE):
                TranslateMessage(message)
                log.debug("Dispatching msg={}".format(repr(message)))
                DispatchMessage(message)
                return True
        except Exception as err:
            log.error(f"Pump error: {err}")
        return False

    def run(self) -> None:
        if platform.system() != "Windows":
            return

        # Raise the error to the main thread from here
        self._jab_wrapper = JavaAccessBridgeWrapper(ignore_callbacks=True)
        self._future.set_result(self._jab_wrapper)
        while not self._quit_event_loop.is_set():
            # The pump is non blocking. If the is no message in the queue
            # wait for 10 milliseconds until check again to prevent too
            # fast loop. The pump needs time to recover, otherwise it gets cluttered and hangs.
            # Possibly a limitation in the Java Access Bridge that needs investigating.
            # TODO: add backoff timer
            if not self._pump_background():
                time.sleep(0.1)

    def stop(self):
        self._quit_event_loop.set()
        self._jab_wrapper = None
        if not self._future.done():
            self._future.cancel()

    def get_wrapper(self) -> JavaAccessBridgeWrapper:
        return self._future.result()
