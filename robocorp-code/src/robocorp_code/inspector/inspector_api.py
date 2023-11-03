import threading
import typing
from queue import Queue
from typing import Literal, Optional

from robocorp_ls_core.basic import overrides
from robocorp_ls_core.protocols import ActionResultDict, IConfig, IEndPoint
from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.web._web_inspector import (
    PickedLocatorTypedDict,
    WebInspector,
)

if typing.TYPE_CHECKING:
    from robocorp_code.inspector.windows.windows_inspector import WindowsInspector

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

    def __init__(self, endpoint: IEndPoint) -> None:
        threading.Thread.__init__(self)
        self._endpoint = endpoint
        self.daemon = True
        self.queue: "Queue[_WebBaseCommand]" = Queue()
        self._finish = False
        self._web_inspector: Optional[WebInspector] = None

    @property
    def web_inspector(self) -> Optional[WebInspector]:
        return self._web_inspector

    def shutdown(self) -> None:
        self._finish = True

    def run(self) -> None:
        self._web_inspector = WebInspector(self._endpoint)

        loop_timeout: float = _DEFAULT_LOOP_TIMEOUT
        item: Optional[_WebBaseCommand]

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


class _WebBaseCommand:
    loop_timeout: Optional[float] = _DEFAULT_LOOP_TIMEOUT

    def __init__(self):
        self.handled_event = threading.Event()

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        pass


class _WebOpenUrlCommand(_WebBaseCommand):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.open(self.url)


class _WebClickLocatorCommand(_WebBaseCommand):
    loop_timeout = None  # Don't change it.

    def __init__(self, locator: str):
        super().__init__()
        self.locator = locator

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return
        page = web_inspector.page(False)
        if not page:
            return

        page.click(self.locator)


class _WebBrowserConfigureCommand(_WebBaseCommand):
    loop_timeout = None  # Don't change it.

    def __init__(self, kwargs: dict):
        super().__init__()
        self.kwargs = kwargs

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        from robocorp_code.playwright import robocorp_browser

        robocorp_browser.configure(**self.kwargs)


class _WebShutdownCommand(_WebBaseCommand):
    loop_timeout = None  # Don't change it.

    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector_thread.shutdown()


class _WebCloseBrowserCommand(_WebBaseCommand):
    def __call__(self, web_inspector_thread: _WebInspectorThread):
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return

        web_inspector.close_browser()


class _WebAsyncPickCommand(_WebBaseCommand):
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

        def on_pick(locator: PickedLocatorTypedDict):
            endpoint.notify("$/webPick", locator)

        web_inspector.pick_async(on_pick)


class _AsyncStopCommand(_WebBaseCommand):
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


class _WindowsInspectorThread(threading.Thread):
    def __init__(self, endpoint: IEndPoint) -> None:
        threading.Thread.__init__(self)
        self._endpoint = endpoint
        self.daemon = True
        self.queue: "Queue[Optional[_WindowsBaseCommand]]" = Queue()
        self._finish = False
        self._windows_inspector: Optional["WindowsInspector"] = None

    @property
    def windows_inspector(self) -> Optional["WindowsInspector"]:
        return self._windows_inspector

    def shutdown(self) -> None:
        self._finish = True
        self.queue.put(None)

    def run(self) -> None:
        from concurrent.futures import Future
        from typing import List

        from robocorp_code.inspector.windows.windows_inspector import (
            ControlLocatorInfoTypedDict,
            WindowsInspector,
        )

        self._windows_inspector = WindowsInspector()

        endpoint = self._endpoint

        def _on_pick(picked: List[ControlLocatorInfoTypedDict]):
            endpoint.notify("$/windowsPick", picked)

        self._windows_inspector.on_pick.register(_on_pick)

        item: Optional[_WindowsBaseCommand]

        while not self._finish:
            try:
                item = self.queue.get()
            except Exception:
                continue

            if item is not None:
                future: Future = item.future
                try:
                    log.debug("-- Start handling command: %s", item)
                    result = item(self)
                    log.debug("-- End handling command: %s", item)
                except Exception as e:
                    log.exception(f"Error handling {item}.")
                    future.set_exception(e)
                else:
                    future.set_result(result)


class _WindowsBaseCommand:
    def __init__(self):
        from concurrent.futures import Future

        self.future = Future()

    def __call__(
        self, windows_inspector_thread: "_WindowsInspectorThread"
    ) -> ActionResultDict:
        raise NotImplementedError()


class _WindowsSetWindowLocator(_WindowsBaseCommand):
    def __init__(self, locator):
        super().__init__()
        self.locator = locator

    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        windows_inspector_thread.windows_inspector.set_window_locator(self.locator)

        return {"success": True, "message": None, "result": None}


class _WindowsStartPick(_WindowsBaseCommand):
    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        windows_inspector_thread.windows_inspector.start_pick()

        return {"success": True, "message": None, "result": None}


class _WindowsStopPick(_WindowsBaseCommand):
    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        windows_inspector_thread.windows_inspector.stop_pick()

        return {"success": True, "message": None, "result": None}


class _WindowsStartHighlight(_WindowsBaseCommand):
    def __init__(
        self,
        locator,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ):
        super().__init__()
        self.locator = locator
        self.search_depth = search_depth
        self.search_strategy = search_strategy

    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        result = windows_inspector_thread.windows_inspector.start_highlight(
            locator=self.locator,
            search_depth=self.search_depth,
            search_strategy=self.search_strategy,
        )

        return {"success": True, "message": None, "result": result}


class _WindowsCollectTree(_WindowsBaseCommand):
    def __init__(
        self,
        locator,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ):
        super().__init__()
        self.locator = locator
        self.search_depth = search_depth
        self.search_strategy = search_strategy

    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        result = windows_inspector_thread.windows_inspector.collect_tree(
            locator=self.locator,
            search_depth=self.search_depth,
            search_strategy=self.search_strategy,
        )

        return {"success": True, "message": None, "result": result}


class _WindowsStopHighlight(_WindowsBaseCommand):
    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        windows_inspector_thread.windows_inspector.stop_highlight()

        return {"success": True, "message": None, "result": None}


class InspectorApi(PythonLanguageServer):
    """
    This is a custom server. It uses the same message-format used in the language
    server but with custom messages (i.e.: this is not the language server, but
    an API to use the bits we need in a separate process).
    """

    def __init__(self, read_from, write_to) -> None:
        PythonLanguageServer.__init__(self, read_from, write_to)
        self.__web_inspector_thread: Optional[_WebInspectorThread] = None
        self.__windows_inspector_thread: Optional[_WindowsInspectorThread] = None

    @property
    def _web_inspector_thread(self):
        # Lazily-initialize
        ret = self.__web_inspector_thread
        if ret is None:
            self.__web_inspector_thread = _WebInspectorThread(self._endpoint)
            self.__web_inspector_thread.start()

        return self.__web_inspector_thread

    @property
    def _windows_inspector_thread(self):
        # Lazily-initialize
        ret = self.__windows_inspector_thread
        if ret is None:
            self.__windows_inspector_thread = _WindowsInspectorThread(self._endpoint)
            self.__windows_inspector_thread.start()

        return self.__windows_inspector_thread

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

    def _enqueue_web(self, cmd: _WebBaseCommand, wait: bool):
        self._web_inspector_thread.queue.put(cmd)
        if wait:
            cmd.handled_event.wait(20)

    def _enqueue_windows(
        self, cmd: _WindowsBaseCommand, wait: bool = True
    ) -> ActionResultDict:
        self._windows_inspector_thread.queue.put(cmd)
        if wait:
            try:
                return cmd.future.result()
            except Exception as e:
                return {"success": False, "message": str(e), "result": None}

        return {"success": True, "message": None, "result": None}

    def m_open_browser(self, url: str, wait: bool = False) -> None:
        self._enqueue_web(_WebOpenUrlCommand(url), wait)

    def m_start_pick(self, url_if_new: str = "", wait: bool = False) -> None:
        self._enqueue_web(_WebAsyncPickCommand(self._endpoint, url_if_new), wait)

    def m_stop_pick(self, wait: bool = False) -> None:
        self._enqueue_web(_AsyncStopCommand(), wait)

    def m_close_browser(self, wait: bool = False) -> None:
        self._enqueue_web(_WebCloseBrowserCommand(), wait)

    def m_click(self, locator: str, wait: bool = False) -> None:
        self._enqueue_web(_WebClickLocatorCommand(locator), wait)

    def m_browser_configure(self, wait=False, **kwargs) -> None:
        self._enqueue_web(_WebBrowserConfigureCommand(kwargs), wait)

    def m_shutdown(self, **_kwargs):
        self._enqueue_web(_WebShutdownCommand(), wait=False)
        PythonLanguageServer.m_shutdown(self, **_kwargs)

    def m_windows_set_window_locator(self, locator: str) -> ActionResultDict:
        return self._enqueue_windows(_WindowsSetWindowLocator(locator))

    def m_windows_start_pick(self) -> ActionResultDict:
        return self._enqueue_windows(_WindowsStartPick())

    def m_windows_stop_pick(self) -> ActionResultDict:
        return self._enqueue_windows(_WindowsStopPick())

    def m_windows_start_highlight(
        self,
        locator,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ) -> ActionResultDict:
        return self._enqueue_windows(
            _WindowsStartHighlight(locator, search_depth, search_strategy)
        )

    def m_windows_collect_tree(
        self,
        locator,
        search_depth: int = 8,
        search_strategy: Literal["siblings", "all"] = "all",
    ) -> ActionResultDict:
        return self._enqueue_windows(
            _WindowsCollectTree(locator, search_depth, search_strategy)
        )

    def m_windows_stop_highlight(self) -> ActionResultDict:
        return self._enqueue_windows(_WindowsStopHighlight())
