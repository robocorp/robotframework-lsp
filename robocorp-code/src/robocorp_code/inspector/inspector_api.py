import threading
from queue import Queue
from typing import Literal, Optional, TYPE_CHECKING, Callable, Tuple, Any

from robocorp_ls_core.basic import overrides
from robocorp_ls_core.protocols import ActionResultDict, IConfig, IEndPoint
from robocorp_ls_core.python_ls import PythonLanguageServer
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.constants import IS_WIN

from robocorp_code.inspector.web._web_inspector import (
    PickedLocatorTypedDict,
    WebInspector,
)

if TYPE_CHECKING:
    from robocorp_code.inspector.windows.windows_inspector import WindowsInspector
    from robocorp_code.inspector.image._image_inspector import ImageInspector
    from robocorp_code.inspector.java.java_inspector import JavaInspector
log = get_logger(__name__)

_DEFAULT_LOOP_TIMEOUT = 5


####
#### WEB COMMANDS
####
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

    def __init__(
        self,
        endpoint: IEndPoint,
        configuration: Optional[dict],
        shutdown_callback: Optional[Callable],
    ) -> None:
        threading.Thread.__init__(self)
        self._endpoint = endpoint
        self.daemon = True
        self.queue: "Queue[Optional[_WebBaseCommand]]" = Queue()
        self._finish = False
        self._web_inspector: Optional[WebInspector] = None
        self._shutdown_callback = shutdown_callback

        self._configuration = configuration

    @property
    def web_inspector(self) -> Optional[WebInspector]:
        return self._web_inspector

    def shutdown(self) -> None:
        if self._shutdown_callback is not None:
            self._shutdown_callback()
        # signal the run to finish
        self._finish = True
        self.queue.put(None)
        if self._web_inspector:
            self._web_inspector.shutdown()

    def run(self) -> None:
        from concurrent.futures import Future

        self._web_inspector = WebInspector(
            endpoint=self._endpoint,
            configuration=self._configuration,
            callback_end_thread=self.shutdown,
        )

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
                    future: Future = item.future
                    try:
                        result = item(self)
                        if item.loop_timeout is not None:
                            loop_timeout = item.loop_timeout
                    except Exception as e:
                        log.exception(f"Error handling {item}: {e}")
                        future.set_exception(e)
                    else:
                        future.set_result(result)
                    finally:
                        item.handled_event.set()
        finally:
            try:
                from robocorp_code.playwright.robocorp_browser._caches import (
                    clear_all_callback,
                )

                if self._web_inspector.page(auto_create=False):
                    clear_all_callback()
            except Exception as e:
                log.exception(f"Clearing callbacks raised Exception:", e)
            log.debug("Exited from Web Inspector Thread!")


class _WebBaseCommand:
    loop_timeout: Optional[float] = _DEFAULT_LOOP_TIMEOUT

    def __init__(self):
        from concurrent.futures import Future

        self.handled_event = threading.Event()
        self.future = Future()

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


class _WebAsyncStopCommand(_WebBaseCommand):
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


class _WebValidateCommand(_WebBaseCommand):
    loop_timeout = None  # Don't change it.

    def __init__(self, locator: dict, url: Optional[str]):
        super().__init__()
        self.locator = locator
        self.url = url

    def __call__(self, web_inspector_thread: _WebInspectorThread) -> dict:
        web_inspector = web_inspector_thread.web_inspector
        if not web_inspector:
            return {
                "success": False,
                "message": f"Web Inspector was not initiated",
                "result": None,
            }
        page = web_inspector.page(False)
        if not page:
            if self.url:
                page = web_inspector.open(self.url)
            if not page:
                return {
                    "success": False,
                    "message": f"Page was not initiated",
                    "result": None,
                }

        frame = self.locator.get("frame", None)
        if self.url is not None and page.url != self.url:
            page.goto(self.url)

        page.wait_for_load_state()
        try:
            matches = web_inspector.find_matches(
                strategy=self.locator["strategy"],
                value=self.locator["value"],
                frame=frame,
            )
            return {
                "success": True,
                "message": None,
                "result": len(matches),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Exception occurred while validating: {e}",
                "result": None,
            }


####
#### WINDOWS COMMANDS
####
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
        if self._windows_inspector:
            self._windows_inspector.shutdown()

    def run(self) -> None:
        from concurrent.futures import Future
        from typing import List

        from robocorp_code.inspector.windows.windows_inspector import (
            ControlLocatorInfoTypedDict,
            WindowsInspector,
        )

        endpoint = self._endpoint

        def _on_pick(picked: List[ControlLocatorInfoTypedDict]):
            endpoint.notify("$/windowsPick", {"picked": picked})

        self._windows_inspector = WindowsInspector()
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


class _WindowsParseLocator(_WindowsBaseCommand):
    def __init__(self, locator):
        super().__init__()
        self.locator = locator

    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        locator = self.locator
        from typing import List

        from robocorp_code.inspector.windows.robocorp_windows._errors import (
            InvalidLocatorError,
        )
        from robocorp_code.inspector.windows.robocorp_windows._match_ast import (
            OrSearchParams,
            SearchParams,
            _build_locator_match,
        )

        try:
            locator_match = _build_locator_match(locator)
            only_ors: List[OrSearchParams] = []
            for params in locator_match.flattened:
                if isinstance(params, OrSearchParams):
                    only_ors.append(params)
                else:
                    if not isinstance(params, SearchParams):
                        raise InvalidLocatorError(
                            "Unable to flatten the or/and conditions as expected in the "
                            "locator.\nPlease report this as an error to robocorp-code."
                            f"\nLocator: {locator}"
                        )
                    if params.empty():
                        raise InvalidLocatorError(
                            "Unable to flatten the or/and conditions as expected in the "
                            "locator.\nPlease report this as an error to robocorp-code."
                            f"\nLocator: {locator}"
                        )
                    only_ors.append(OrSearchParams(params))

            # It worked (although it may still have warnings to the user).
            return {
                "success": True,
                "message": "\n".join(locator_match.warnings),
                "result": None,
            }
        except Exception as e:
            # It failed
            return {"success": False, "message": str(e), "result": None}


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


class _WindowsList(_WindowsBaseCommand):
    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        result = windows_inspector_thread.windows_inspector.list_windows()
        return {"success": True, "message": None, "result": result}


class _WindowsStopHighlight(_WindowsBaseCommand):
    def __call__(
        self, windows_inspector_thread: _WindowsInspectorThread
    ) -> ActionResultDict:
        if not windows_inspector_thread.windows_inspector:
            raise RuntimeError("windows_inspector not initialized.")
        windows_inspector_thread.windows_inspector.stop_highlight()
        return {"success": True, "message": None, "result": None}


####
#### IMAGE COMMANDS
####
class _ImageInspectorThread(threading.Thread):
    def __init__(self, endpoint: IEndPoint) -> None:
        threading.Thread.__init__(self)
        self._endpoint = endpoint
        self.daemon = True
        self.queue: "Queue[Optional[_ImageBaseCommand]]" = Queue()
        self._finish = False
        self._image_inspector: Optional["ImageInspector"] = None

    @property
    def image_inspector(self) -> Optional["ImageInspector"]:
        return self._image_inspector

    def shutdown(self) -> None:
        self._finish = True
        self.queue.put(None)
        if self._image_inspector:
            self._image_inspector.shutdown()

    def run(self) -> None:
        from concurrent.futures import Future
        from robocorp_code.inspector.image._image_inspector import ImageInspector

        endpoint = self._endpoint

        def _on_pick(picked: dict):
            endpoint.notify("$/imagePick", {"picked": picked})

        def _on_validate(matches: int):
            endpoint.notify("$/imageValidation", {"matches": matches})

        self._image_inspector = ImageInspector(endpoint=endpoint)
        self._image_inspector.on_pick.register(_on_pick)
        self._image_inspector.on_validate.register(_on_validate)

        item: Optional[_ImageBaseCommand]

        while not self._finish:
            try:
                item = self.queue.get()
            except Exception:
                continue

            if item is not None:
                future: Future = item.future
                try:
                    result = item(self)
                except Exception as e:
                    log.exception(f"Error handling {item}.")
                    future.set_exception(e)
                else:
                    future.set_result(result)


class _ImageBaseCommand:
    loop_timeout: Optional[float] = _DEFAULT_LOOP_TIMEOUT

    def __init__(self):
        from concurrent.futures import Future

        self.handled_event = threading.Event()
        self.future = Future()

    def __call__(self, image_inspector_thread: _ImageInspectorThread):
        pass


class _ImageStartPick(_ImageBaseCommand):
    def __init__(
        self, minimize: Optional[bool] = None, confidence_level: Optional[int] = None
    ) -> None:
        super().__init__()
        self.minimize = minimize
        self.confidence_level = confidence_level

    def __call__(
        self, image_inspector_thread: _ImageInspectorThread
    ) -> ActionResultDict:
        if not image_inspector_thread.image_inspector:
            raise RuntimeError("image_inspector not initialized.")
        image_inspector_thread.image_inspector.start_pick(self.confidence_level)
        return {"success": True, "message": None, "result": None}


class _ImageStopPick(_ImageBaseCommand):
    def __call__(
        self, image_inspector_thread: _ImageInspectorThread
    ) -> ActionResultDict:
        if not image_inspector_thread.image_inspector:
            raise RuntimeError("image_inspector not initialized.")
        image_inspector_thread.image_inspector.stop_pick()
        return {"success": True, "message": None, "result": None}


# TODO: replace this implementation when the robocorp library has image recognition
class _ImageValidateLocator(_ImageBaseCommand):
    def __init__(self, locator: dict, confidence_level: Optional[int] = None) -> None:
        super().__init__()
        self.locator = locator
        self.confidence_level = confidence_level

    def __call__(
        self, image_inspector_thread: _ImageInspectorThread
    ) -> ActionResultDict:
        if not image_inspector_thread.image_inspector:
            raise RuntimeError("image_inspector not initialized.")
        image_inspector_thread.image_inspector.validate(
            image_base64=self.locator["screenshot"], confidence=self.confidence_level
        )
        return {"success": True, "message": None, "result": None}


class _ImageSaveImage(_ImageBaseCommand):
    def __init__(self, root_directory: str, image_base64: str) -> None:
        super().__init__()
        self.root_directory = root_directory
        self.image_base64 = image_base64

    def __call__(
        self, image_inspector_thread: _ImageInspectorThread
    ) -> ActionResultDict:
        if not image_inspector_thread.image_inspector:
            raise RuntimeError("image_inspector not initialized.")
        result = image_inspector_thread.image_inspector.save_image(
            root_directory=self.root_directory, image_base64=self.image_base64
        )
        return {"success": True, "message": None, "result": result}


####
#### JAVA COMMANDS
####
class _JavaInspectorThread(threading.Thread):
    def __init__(self, endpoint: IEndPoint) -> None:
        threading.Thread.__init__(self)
        self._endpoint = endpoint
        self.daemon = True
        self.queue: "Queue[Optional[_JavaBaseCommand]]" = Queue()
        self._finish = False
        self._java_inspector: Optional["JavaInspector"] = None

    @property
    def java_inspector(self) -> Optional["JavaInspector"]:
        return self._java_inspector

    def shutdown(self) -> None:
        self._finish = True
        self.queue.put(None)
        if self._java_inspector:
            self._java_inspector.shutdown()

    def run(self) -> None:
        from concurrent.futures import Future

        from robocorp_code.inspector.java.java_inspector import (
            JavaInspector,
        )

        endpoint = self._endpoint

        def _on_pick(picked: Any):
            endpoint.notify("$/javaPick", {"picked": picked})

        self._java_inspector = JavaInspector()
        self._java_inspector.on_pick.register(_on_pick)

        item: Optional[_JavaBaseCommand]

        while not self._finish:
            try:
                item = self.queue.get()
            except Exception:
                continue

            if item is not None:
                future: Future = item.future
                try:
                    log.debug("JavaInspectorThread: Start handling command: %s", item)
                    result = item(self)
                    log.debug("JavaInspectorThread: End handling command: %s", item)
                except Exception as e:
                    log.exception(f"Error handling {item}.")
                    future.set_exception(e)
                else:
                    future.set_result(result)


class _JavaBaseCommand:
    def __init__(self):
        from concurrent.futures import Future

        self.future = Future()

    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        raise NotImplementedError()


class _JavaSetWindowLocator(_JavaBaseCommand):
    def __init__(self, locator):
        super().__init__()
        self.locator = locator

    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        java_inspector_thread.java_inspector.set_window_locator(self.locator)

        return {"success": True, "message": None, "result": None}


class _JavaStartPick(_JavaBaseCommand):
    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        java_inspector_thread.java_inspector.start_pick()

        return {"success": True, "message": None, "result": None}


class _JavaParseLocator(_JavaBaseCommand):
    def __init__(self, locator):
        super().__init__()
        self.locator = locator

    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        locator = self.locator

        from robocorp_code.inspector.java.robocorp_java._locators import parse_locator

        try:
            matches = parse_locator(locator)
            return {
                "success": True,
                "message": None
                if len(matches) > 0
                else "Locator could not be validated correctly. Please make sure the syntax is correct.",
                "result": None,
            }
        except Exception as e:
            # It failed
            return {"success": False, "message": str(e), "result": None}


class _JavaStopPick(_JavaBaseCommand):
    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        java_inspector_thread.java_inspector.stop_pick()
        return {"success": True, "message": None, "result": None}


class _JavaStartHighlight(_JavaBaseCommand):
    def __init__(
        self,
        locator: str,
        search_depth: int = 8,
    ):
        super().__init__()
        self.locator = locator
        self.search_depth = search_depth

    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        result = java_inspector_thread.java_inspector.start_highlight(
            locator=self.locator,
            search_depth=self.search_depth,
        )
        return {"success": True, "message": None, "result": result}


class _JavaCollectTree(_JavaBaseCommand):
    def __init__(
        self,
        locator: str,
        search_depth: int = 8,
    ):
        super().__init__()
        self.locator = locator
        self.search_depth = search_depth

    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        result = java_inspector_thread.java_inspector.collect_tree(
            locator=self.locator,
            search_depth=self.search_depth,
        )
        return {"success": True, "message": None, "result": result}


class _JavaListApplications(_JavaBaseCommand):
    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        result = java_inspector_thread.java_inspector.list_opened_applications()
        return {"success": True, "message": None, "result": result}


class _JavaStopHighlight(_JavaBaseCommand):
    def __call__(self, java_inspector_thread: _JavaInspectorThread) -> ActionResultDict:
        if not java_inspector_thread.java_inspector:
            raise RuntimeError("java_inspector not initialized.")
        java_inspector_thread.java_inspector.stop_highlight()
        return {"success": True, "message": None, "result": None}


####
#### INSPECTOR API
####
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
        self.__image_inspector_thread: Optional[_ImageInspectorThread] = None
        self.__java_inspector_thread: Optional[_JavaInspectorThread] = None

        # set default configuration for the inspectors
        self.__web_inspector_configuration: dict = {  # configuring the Web Inspector with defaults
            "browser_config": {  # set the default viewport size
                "viewport_size": (1280, 720),
                # if there is an attempted download & install sequence, do it in the isolated env
                "isolated": True,
                # always pick chromium
                "browser_engine": "chromium",
            },
            "url": "",
        }

    def __nullify_web_inspector_thread(self):
        # make sure we nullify the thread
        self.__web_inspector_thread = None

    @property
    def _web_inspector_thread(self):
        # Lazily-initialize
        ret = self.__web_inspector_thread
        if ret is None:
            self.__web_inspector_thread = _WebInspectorThread(
                endpoint=self._endpoint,
                configuration=self.__web_inspector_configuration,
                shutdown_callback=self.__nullify_web_inspector_thread,
            )
            self.__web_inspector_thread.start()

        return self.__web_inspector_thread

    @property
    def _windows_inspector_thread(self):
        # Lazily-initialize
        ret = self.__windows_inspector_thread
        if ret is None and IS_WIN:
            self.__windows_inspector_thread = _WindowsInspectorThread(self._endpoint)
            self.__windows_inspector_thread.start()

        return self.__windows_inspector_thread

    @property
    def _image_inspector_thread(self):
        # Lazily-initialize
        ret = self.__image_inspector_thread
        if ret is None:
            self.__image_inspector_thread = _ImageInspectorThread(self._endpoint)
            self.__image_inspector_thread.start()

        return self.__image_inspector_thread

    @property
    def _java_inspector_thread(self):
        # Lazily-initialize
        ret = self.__java_inspector_thread
        if ret is None and IS_WIN:
            self.__java_inspector_thread = _JavaInspectorThread(self._endpoint)
            self.__java_inspector_thread.start()

        return self.__java_inspector_thread

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

    def m_kill_inspectors(self, inspector: Optional[str]):
        log.debug(
            "Man:: Will kill inspector:", inspector if inspector is not None else "ALL"
        )
        if self.__web_inspector_thread and (
            inspector == "browser" or inspector is None
        ):
            self.__web_inspector_thread.shutdown()
            self.__web_inspector_thread = None
            log.debug("Man:: Killed Web Inspector!")
        if self.__windows_inspector_thread and (
            inspector == "windows" or inspector is None
        ):
            self.__windows_inspector_thread.shutdown()
            self.__windows_inspector_thread = None
            log.debug("Man:: Killed Windows Inspector!")
        if self.__java_inspector_thread and (inspector == "java" or inspector is None):
            self.__java_inspector_thread.shutdown()
            self.__java_inspector_thread = None
            log.debug("Man:: Killed Java Inspector!")
        if self.__image_inspector_thread and (
            inspector == "image" or inspector is None
        ):
            self.__image_inspector_thread.shutdown()
            self.__image_inspector_thread = None
            log.debug("Man:: Killed Image Inspector!")

    ####
    #### ENQUEUE COMMANDS TO THREAD WORKERS
    ####
    def _enqueue_web(self, cmd: _WebBaseCommand, wait: bool):
        if self._web_inspector_thread:
            self._web_inspector_thread.queue.put(cmd)
            if wait:
                cmd.handled_event.wait(20)
                try:
                    return cmd.future.result()
                except Exception as e:
                    return {"success": False, "message": str(e), "result": None}

        return {"success": True, "message": None, "result": None}

    def _enqueue_windows(
        self, cmd: _WindowsBaseCommand, wait: bool = True
    ) -> ActionResultDict:
        if self._windows_inspector_thread:
            self._windows_inspector_thread.queue.put(cmd)
            if wait:
                try:
                    return cmd.future.result()
                except Exception as e:
                    return {"success": False, "message": str(e), "result": None}

        return {"success": True, "message": None, "result": None}

    def _enqueue_image(
        self, cmd: _ImageBaseCommand, wait: bool = True
    ) -> ActionResultDict:
        if self._image_inspector_thread:
            self._image_inspector_thread.queue.put(cmd)
            if wait:
                try:
                    return cmd.future.result()
                except Exception as e:
                    return {"success": False, "message": str(e), "result": None}

        return {"success": True, "message": None, "result": None}

    def _enqueue_java(
        self, cmd: _JavaBaseCommand, wait: bool = True
    ) -> ActionResultDict:
        if self._java_inspector_thread:
            self._java_inspector_thread.queue.put(cmd)
            if wait:
                try:
                    return cmd.future.result()
                except Exception as e:
                    return {"success": False, "message": str(e), "result": None}

        return {"success": True, "message": None, "result": None}

    ####
    #### WEB RELATED APIs
    ####

    def m_open_browser(self, url: str, wait: bool = False) -> None:
        self._enqueue_web(_WebOpenUrlCommand(url), wait)

    def m_start_pick(self, url_if_new: str = "", wait: bool = False) -> None:
        # configure
        if self.__web_inspector_configuration:
            self.__web_inspector_configuration["url"] = url_if_new
        else:
            self.__web_inspector_configuration = {"url": url_if_new}
        # command
        self._enqueue_web(_WebAsyncPickCommand(self._endpoint, url_if_new), wait)

    def m_stop_pick(self, wait: bool = False) -> None:
        self._enqueue_web(_WebAsyncStopCommand(), wait)

    def m_close_browser(self, wait: bool = False) -> None:
        self._enqueue_web(_WebCloseBrowserCommand(), wait)

    def m_click(self, locator: str, wait: bool = False) -> None:
        self._enqueue_web(_WebClickLocatorCommand(locator), wait)

    def m_browser_configure(
        self,
        wait=False,
        viewport_size: Optional[Tuple] = None,
        url: Optional[str] = None,
    ) -> None:
        # configure
        self.__web_inspector_configuration["browser_config"][
            "viewport_size"
        ] = viewport_size
        self.__web_inspector_configuration["url"] = url
        # command
        self._enqueue_web(
            _WebBrowserConfigureCommand(
                self.__web_inspector_configuration["browser_config"]
            ),
            wait,
        )

    def m_shutdown(self, **_kwargs) -> None:
        self._enqueue_web(_WebShutdownCommand(), wait=False)
        PythonLanguageServer.m_shutdown(self, **_kwargs)

    def m_validate_locator(
        self, locator: dict, url: Optional[str], wait: bool = False
    ) -> int:
        return self._enqueue_web((_WebValidateCommand(locator=locator, url=url)), wait)

    ####
    #### WINDOWS RELATED APIs
    ####

    def m_windows_parse_locator(self, locator: str) -> ActionResultDict:
        return self._enqueue_windows(_WindowsParseLocator(locator))

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

    def m_windows_list_windows(
        self,
    ) -> ActionResultDict:
        return self._enqueue_windows(_WindowsList())

    def m_windows_stop_highlight(self) -> ActionResultDict:
        return self._enqueue_windows(_WindowsStopHighlight())

    ####
    #### IMAGE RELATED APIs
    ####

    def m_image_start_pick(
        self, minimize: Optional[bool] = None, confidence_level: Optional[int] = None
    ):
        return self._enqueue_image(
            _ImageStartPick(confidence_level=confidence_level, minimize=minimize)
        )

    def m_image_stop_pick(self):
        return self._enqueue_image(_ImageStopPick())

    def m_image_validate_locator(
        self, locator: dict, confidence_level: Optional[int] = None
    ):
        return {"success": True, "message": None, "result": None}
        # TODO: replace this implementation when the robocorp library has image recognition
        # return self._enqueue_image(
        #     _ImageValidateLocator(locator=locator, confidence_level=confidence_level)
        # )

    def m_image_save_image(self, root_directory: str, image_base64: str):
        return self._enqueue_image(_ImageSaveImage(root_directory, image_base64))

    ####
    #### JAVA RELATED APIs
    ####

    def m_java_parse_locator(self, locator: str) -> ActionResultDict:
        return self._enqueue_java(_JavaParseLocator(locator))

    def m_java_set_window_locator(self, locator: str) -> ActionResultDict:
        return self._enqueue_java(_JavaSetWindowLocator(locator))

    def m_java_start_pick(self) -> ActionResultDict:
        return self._enqueue_java(_JavaStartPick())

    def m_java_stop_pick(self) -> ActionResultDict:
        return self._enqueue_java(_JavaStopPick())

    def m_java_start_highlight(
        self,
        locator,
        search_depth: int = 8,
    ) -> ActionResultDict:
        return self._enqueue_java(_JavaStartHighlight(locator, search_depth))

    def m_java_collect_tree(
        self,
        locator,
        search_depth: int = 8,
    ) -> ActionResultDict:
        return self._enqueue_java(_JavaCollectTree(locator, search_depth))

    def m_java_list_windows(
        self,
    ) -> ActionResultDict:
        return self._enqueue_java(_JavaListApplications())

    def m_java_stop_highlight(self) -> ActionResultDict:
        return self._enqueue_java(_JavaStopHighlight())
