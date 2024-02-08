import ctypes
import queue
import threading
import time

from JABWrapper.jab_wrapper import JavaAccessBridgeWrapper
from robocorp_ls_core.robotframework_log import get_logger

PeekMessage = ctypes.windll.user32.PeekMessageW
GetMessage = ctypes.windll.user32.GetMessageW
TranslateMessage = ctypes.windll.user32.TranslateMessage
DispatchMessage = ctypes.windll.user32.DispatchMessageW

log = get_logger(__name__)


REMOVE_FROM_QUEUE = 0x0001


class _EventPumpThread(threading.Thread):
    def __init__(
        self,
    ) -> None:
        super().__init__()
        # Jab wrapper needs to be part of the thread that pumps the window events
        self._jab_wrapper: JavaAccessBridgeWrapper = None
        self._queue = queue.Queue()
        self._quit_queue_loop = threading.Event()

    def _pump_background(self) -> bool:
        try:
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
        finally:
            log.info("Stopped processing events")
        return False

    def run(self) -> None:
        self._jab_wrapper = JavaAccessBridgeWrapper(ignore_callbacks=True)
        self._queue.put(self._jab_wrapper)
        while not self._quit_queue_loop.is_set():
            # The pump is non blocking. If the is no message in the queue
            # wait for 10 milliseconds until check again to prevent too
            # fast loop.
            # TODO: add backoff timer
            if not self._pump_background():
                time.sleep(0.01)

    def stop(self):
        self._quit_queue_loop.set()
        self._jab_wrapper = None

    def get_wrapper(self) -> JavaAccessBridgeWrapper:
        return self._queue.get()
