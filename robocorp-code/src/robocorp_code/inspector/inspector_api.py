import threading
from queue import Queue
from typing import Dict, List, Optional, Tuple

from robocorp_ls_core.basic import overrides
from robocorp_ls_core.protocols import IConfig, IEndPoint
from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.web._web_inspector import (
    LocatorNameToLocatorTypedDict,
    WebInspector,
)

log = get_logger(__name__)

_DEFAULT_LOOP_TIMEOUT = 5


class _WebInspectorThread(threading.Thread):
    """
    This is a little tricky:

    Playwright internally requires an event loop which is abstracted away from
    us in most cases (as we're just dealing with the page directly and we'd be
    waiting for it), but in our use case, we actually have 2 loops, one which
    is related to dealing with received messages and the other one which is
    the playwright event loop.

    Note: if the pick wasn't async we could do without this additional layer,
    but then we wouldn't be able to receive messages while the user is doing a
    pick.
    """

    def __init__(self) -> None:
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue: "Queue[_BaseCommand]" = Queue()
        self._finish = False
        self._web_inspector: Optional[WebInspector] = None

    @property
    def web_inspector(self) -> Optional[WebInspector]:
        return self._web_inspector

    def shutdown(self) -> None:
        self._finish = True

    def run(self) -> None:
        self._web_inspector = WebInspector()

        loop_timeout: float = _DEFAULT_LOOP_TIMEOUT
        item: Optional[_BaseCommand]

        try:
            while not self._finish:
                try:
                    item = self.queue.get(timeout=loop_timeout)
                except Exception:
                    self._web_inspector.loop()
                    continue

                if item is not None:
                    try:
                        log.debug("-- Start handling command: %s", item)
                        item(self)
                        log.debug("-- End handling command: %s", item)
                        if item.loop_timeout is not None:
                            loop_timeout = item.loop_timeout
                    except Exception:
                        log.exception(f"Error handling {item}.")
                    finally:
                        item.handled_event.set()
        finally:
            from robocorp_code.playwright.robocorp_browser._caches import (
                clear_all_callback,
            )

            clear_all_callback()


class _BaseCommand:
    loop_timeout: Optional[float] = _DEFAULT_LOOP_TIMEOUT

    def __init__(self):
        self.handled_event = threading.Event()

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        pass


class _OpenUrlCommand(_BaseCommand):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.open(self.url)


class _ClickLocatorCommand(_BaseCommand):
    loop_timeout = None  # Don't change it.

    def __init__(self, locator: str):
        super().__init__()
        self.locator = locator

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.page().click(self.locator)


class _BrowserConfigureCommand(_BaseCommand):
    loop_timeout = None  # Don't change it.

    def __init__(self, kwargs: dict):
        super().__init__()
        self.kwargs = kwargs

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        from robocorp_code.playwright import robocorp_browser

        robocorp_browser.configure(**self.kwargs)


class _ShutdownCommand(_BaseCommand):
    loop_timeout = None  # Don't change it.

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector_thread.shutdown()


class _CloseBrowserCommand(_BaseCommand):
    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.close_browser()


class _AsyncPickCommand(_BaseCommand):
    # The async pick is only done when playwright is in the loop, so,
    # this needs to be small.
    loop_timeout = 1 / 15

    def __init__(self, endpoint: IEndPoint, url_if_new: str = ""):
        super().__init__()
        self.endpoint = endpoint
        self.url_if_new = url_if_new

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        if self.url_if_new:
            web_inspector.open_if_new(self.url_if_new)

        endpoint = self.endpoint

        def on_pick(locator: Dict):
            web_inspector_thread.queue.put(_MakeFullLocatorsCommand(endpoint, locator))

        web_inspector.pick_async(on_pick)


class _MakeFullLocatorsCommand(_BaseCommand):
    def __init__(self, endpoint: IEndPoint, locator):
        super().__init__()
        self.endpoint = endpoint
        self.locator = locator

    def _send_pick(self, locator: LocatorNameToLocatorTypedDict):
        self.endpoint.notify("$/webPick", locator)

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        # full_locators = web_inspector.make_full_locators(self.locator)
        self._send_pick(self.locator)


class _AsyncStopCommand(_BaseCommand):
    # The async pick is only done when playwright is in the loop, so,
    # this needs to be small.
    loop_timeout = 1 / 15

    def __init__(self):
        super().__init__()

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.stop_pick_async()


class InspectorApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need from robotframework in a separate process).
    """

    def __init__(
        self,
        read_from,
        write_to,
    ):
        PythonLanguageServer.__init__(self, read_from, write_to)
        self._web_inspector_thread = _WebInspectorThread()
        self._web_inspector_thread.start()

    def _create_config(self) -> IConfig:
        from robocorp_code.robocorp_config import RobocorpConfig

        return RobocorpConfig()

    @overrides(PythonLanguageServer.lint)
    def lint(self, *args, **kwargs):
        pass  # No-op for this server.

    @overrides(PythonLanguageServer.cancel_lint)
    def cancel_lint(self, *args, **kwargs):
        pass  # No-op for this server.

    def m_echo(self, arg):
        return "echo", arg

    def _enqueue(self, cmd: _BaseCommand, wait: bool):
        self._web_inspector_thread.queue.put(cmd)
        if wait:
            cmd.handled_event.wait(20)

    def m_open_browser(self, url: str, wait: bool = False) -> None:
        self._enqueue(_OpenUrlCommand(url), wait)

    def m_start_pick(self, url_if_new: str = "", wait: bool = False) -> None:
        self._enqueue(_AsyncPickCommand(self._endpoint, url_if_new), wait)

    def m_stop_pick(self, wait: bool = False) -> None:
        self._enqueue(_AsyncStopCommand(), wait)

    def m_close_browser(self, wait: bool = False) -> None:
        self._enqueue(_CloseBrowserCommand(), wait)

    def m_click(self, locator: str, wait: bool = False) -> None:
        self._enqueue(_ClickLocatorCommand(locator), wait)

    def m_browser_configure(self, wait=False, **kwargs) -> None:
        self._enqueue(_BrowserConfigureCommand(kwargs), wait)

    def m_shutdown(self, **_kwargs):
        self._enqueue(_ShutdownCommand(), wait=False)
        PythonLanguageServer.m_shutdown(self, **_kwargs)
