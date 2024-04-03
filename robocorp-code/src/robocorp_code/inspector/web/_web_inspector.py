import json
import threading
import time
import weakref
from typing import Callable, List, Optional, Tuple
from string import Template

from playwright.sync_api import ElementHandle
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core.protocols import IEndPoint, TypedDict
from robocorp_ls_core.robotframework_log import get_logger

from robocorp_code.inspector.common import (
    STATE_CLOSED,
    STATE_INITIALIZING,
    STATE_NOT_PICKING,
    STATE_OPENED,
    STATE_PICKING,
)

log = get_logger(__name__)


def _load_resource(name):
    from robocorp_code.inspector.web import WEB_RESOURCES_DIR

    inspector_js = WEB_RESOURCES_DIR / name
    return inspector_js.read_text(encoding="utf-8")


# Async mode (will start a pick and when the pick is
# done an event will be sent).
# It'll keep picking until cancelled.
_ASYNC_MULTI_PICK_CODE = """
()=>{
    var callback = (picked)=>{
        on_picked(picked);
    }

    var iFrame = $iFrame;
    var nonStopRun = true;
    Inspector.startPicker(callback, nonStopRun, iFrame);
}
"""

_ASYNC_CANCEL_PICK_CODE = """
()=>{
    Inspector.cancelPick();
}
"""


class LocatorStrategyAlternativeTypedDict(TypedDict):
    strategy: str
    value: str
    matches: int


class PickedLocatorTypedDict(TypedDict):
    type: str  # 'browser'
    source: str  # path to file
    strategy: str
    value: str
    element: dict
    alternatives: List[LocatorStrategyAlternativeTypedDict]
    screenshot: str  # data:image/png;base64,iVBORw0KGgoA
    frame: dict


class WebInspector:
    def __init__(
        self,
        endpoint: Optional[IEndPoint] = None,
        configuration: Optional[dict] = None,
        callback_end_thread: Optional[Callable] = None,
    ) -> None:
        """
        Args:
            endpoint: If given notifications on the state will be given.
        """
        self._page: Optional[Page] = None
        self._page_former_url: str = ""

        self._on_picked = Callback()
        self._current_thread = threading.current_thread()
        self._picking = False
        self._pick_async_code_evaluate_worked = False
        self._looping = False
        self._last_picker_check: int = 0
        self._endpoint = endpoint

        self._configuration = configuration
        self._callback_end_thread = callback_end_thread

    @property
    def picking(self):
        return self._picking

    def _check_thread(self):
        assert self._current_thread is threading.current_thread()

    def loop(self):
        self._check_thread()

        if self._looping:
            return
        self._looping = True
        try:
            page = self._page
            if page is not None and not page.is_closed():
                try:
                    for _i in range(2):
                        page.wait_for_timeout(1)  # Just wait for a millisecond.

                        if self._picking:
                            curtime = time.monotonic()
                            if curtime - self._last_picker_check > 0.1:
                                # Check at most once / 100 millis.
                                self._last_picker_check = curtime
                                # If picking is on we re-enable it if it's not currently
                                # enabled.
                                self._verify_pick_state("loop", page)
                except PlaywrightError as e:
                    # If the page is closed while we're looping we may get an exception
                    # (don't let it out).
                    log.debug(f"Handled (expected) error on loop: %s", e)
        finally:
            self._looping = False

    def close_browser(self, skip_notify: bool = False):
        from robocorp_code.playwright import robocorp_browser

        self._check_thread()

        if self._endpoint is not None and not skip_notify:
            self._endpoint.notify("$/webInspectorState", {"state": STATE_CLOSED})

        page = self._page
        if page is not None and not page.is_closed():
            page.close()

        # we need to trigger the thread to end when the browser is closed
        if self._callback_end_thread is not None:
            self._callback_end_thread()
            # we have to close the browser after we trigger the thread close end
            # as the browser.close seem to do the intended task but it hangs afterwards
            # issue: https://github.com/microsoft/playwright/issues/5327
            browser = robocorp_browser.browser()
            if browser:
                browser.close()

    def page(self, auto_create) -> Optional[Page]:
        from robocorp_code.inspector.inspector_api import _WebInspectorThread

        self._check_thread()

        self.loop()

        page = self._page
        if page is None or page.is_closed():
            if not auto_create:
                return None

            endpoint = self._endpoint
            if endpoint is not None:
                endpoint.notify("$/webInspectorState", {"state": STATE_INITIALIZING})

            from robocorp_code.playwright import robocorp_browser

            try:
                log.debug(f"Page is None or Closed. Creating a new one...")
                page = robocorp_browser.page()
                self._page = page
            except Exception as e:
                log.error(f"Exception raised while constructing browser page:", e)
                # shut down the current thread
                if isinstance(self._current_thread, _WebInspectorThread):
                    # make sure we close the browser first - skip notification because we reignite
                    self.close_browser(skip_notify=True)
                    # shutdown the thread
                    self._current_thread.shutdown()
                # # make sure we notify the necessary entities that we want to reignite the thread
                if self._endpoint is not None:
                    self._endpoint.notify("$/webReigniteThread", self._configuration)
                return None

            if endpoint is not None:
                endpoint.notify("$/webInspectorState", {"state": STATE_OPENED})

            weak_self = weakref.ref(self)

            def mark_closed(*args, **kwargs):
                log.debug(f"Mark page closed")
                s = weak_self()
                if s is not None:
                    # make sure we close the browser first
                    self.close_browser()

                    # nullify zone
                    s._page = None
                    self._looping = False
                    self._picking = False
                    self._pick_async_code_evaluate_worked = False

                # shut down the current thread
                if isinstance(self._current_thread, _WebInspectorThread):
                    self._current_thread.shutdown()

            def mark_url_changed(*args, **kwargs):
                if self._page_former_url == "":
                    self._page_former_url = self._page.url
                    if endpoint is not None:
                        endpoint.notify(
                            "$/webURLChange", {"url": self._page_former_url}
                        )
                    return
                if self._page.url != self._page_former_url:
                    self._page_former_url = self._page.url
                    if endpoint is not None:
                        endpoint.notify(
                            "$/webURLChange", {"url": self._page_former_url}
                        )
                    return

            page.on("close", mark_closed)
            page.on("crash", mark_closed)
            page.on("framenavigated", mark_url_changed)

            def on_picked(*args, **kwargs):
                log.debug(f"Web:: Picked item: {args}")
                s = weak_self()
                if s is not None:
                    s._on_picked(*args, **kwargs)
                else:
                    log.debug(f"Inspector instance was lost...")

            try:
                page.expose_function("on_picked", on_picked)
            except PlaywrightError:
                log.exception()
                return None

        return page

    def start_log_console(self):
        """
        Can be used to show all the console messages being received from the browser.
        """
        page = self.page(False)

        def dbg(*args):
            log.debug(*[str(x) for x in args])

        page.on("console", dbg)

    def open(self, url: str) -> Optional[Page]:
        self._check_thread()
        self.loop()

        page = self.page(True)
        if page is None:
            return None
        if url:
            page.goto(url, timeout=30000, wait_until="load")
        return page

    def open_if_new(self, url_if_new):
        self._check_thread()

        self.loop()

        page = self._page
        if page is None or page.is_closed():
            self.open(url_if_new)

    def construct_locator_query(self, strategy, value) -> str:
        self._check_thread()
        strategy = strategy.split(":")[0]
        if strategy == "id":
            return f"#{value}"
        elif strategy == "css":
            return value
        elif strategy == "xpath":
            return f"xpath={value}"
        elif strategy == "link":
            return f"a:has-text({value!r})"
        elif strategy == "name":
            return f"[name={value!r}]"
        else:
            raise ValueError(f"Unexpected strategy: {strategy} (value: {value}).")

        # Note: these 2 were referenced in the selenium version but I (fabioz)
        # didn't find how the picker would generate these, so, keeping those
        # out for now.
        # "class": By.CLASS_NAME,
        # "tag": By.TAG_NAME,

    def construct_frame_query(self, frame) -> Optional[str]:
        frameQuery = ""
        if frame is not None:
            if "props" in frame and frame["props"] is not None:
                props = frame["props"]
                if "id" in props and props["id"]:
                    frameQuery = f'id="{props["id"]}"'
                elif "name" in props and props["name"]:
                    frameQuery = f'name="{props["name"]}"'
                elif "title" in props and props["title"]:
                    frameQuery = f'title="{props["title"]}"'
                elif "class" in props and props["class"]:
                    frameQuery = f'{props["class"]}'
        if frameQuery == "":
            return None

        return f"iframe[{frameQuery}]"

    def _query(self, selector):
        self._check_thread()
        page = self.page(False)
        if page is None:
            return []
        log.debug(f"Query: page.query_selector_all('{selector}')")
        return page.query_selector_all(selector)

    def _query_frame(self, frame_selector, selector):
        self._check_thread()
        page = self.page(False)
        if page is None:
            return []
        log.debug(
            f'Query: page.frame_locator("{frame_selector}").locator("{selector}").all()'
        )
        return page.frame_locator(frame_selector).locator(selector).all()

    def find_matches(
        self, strategy, value, frame: Optional[dict] = None
    ) -> List[ElementHandle]:
        self._check_thread()
        locator_query = self.construct_locator_query(strategy, value)
        frame_query = None
        if frame is not None and frame.get("props", None) is not None:
            is_main = frame.get("props", {}).get("isMain", None)
            if not is_main:
                frame_query = self.construct_frame_query(frame)
        found_matches = (
            self._query(locator_query)
            if frame_query is None
            else self._query_frame(frame_query, locator_query)
        )
        return found_matches

    def pick_async(self, on_picked: Callable[[PickedLocatorTypedDict], None]) -> bool:
        """
        Starts the picker and calls `on_picked(locators)` afterwards.

        Returns:
            True if the given function was registered as the picker function
            and False otherwise.

        Note: if already picking this will not do anything (only one picker callback can be registered at a time).
        """
        self._check_thread()
        self._picking = True
        self._pick_async_code_evaluate_worked = False

        endpoint = self._endpoint
        if endpoint is not None:
            endpoint.notify("$/webInspectorState", {"state": STATE_PICKING})

        if len(self._on_picked) == 0:
            self._on_picked.register(on_picked)

        page = self.page(True)
        if page is None:
            return False
        return self._verify_pick_state("pick (async)", page)

    def _verify_pick_state(self, reason: str, page):
        """
        Args:
            reason: The reason for verifying the pick state.
            page: The page which should be checked.
        """
        if self._picking:
            if self.is_picker_injected(page):
                if not self._pick_async_code_evaluate_worked:
                    try:
                        self.evaluate_in_all_iframes(
                            page, _ASYNC_MULTI_PICK_CODE, inject_frame_data=True
                        )
                        self._pick_async_code_evaluate_worked = True
                    except Exception:
                        log.exception("Error enabling async pick mode.")
                return True

            if not self.inject_picker(reason):
                return False

            try:
                self.evaluate_in_all_iframes(
                    page, _ASYNC_MULTI_PICK_CODE, inject_frame_data=True
                )
                self._pick_async_code_evaluate_worked = True
            except Exception:
                log.exception("Error enabling async pick mode.")
            return True
        return False

    def stop_pick_async(self):
        self._picking = False
        self._check_thread()

        self._on_picked.clear()

        page = self.page(False)
        if page is not None:
            try:
                self.evaluate_in_all_iframes(page, _ASYNC_CANCEL_PICK_CODE)
            except Exception:
                log.exception("Error evaluating cancel pick code.")

        if self._endpoint is not None:
            self._endpoint.notify("$/webInspectorState", {"state": STATE_NOT_PICKING})

    def is_picker_injected(self, page=None) -> bool:
        self._check_thread()
        if page is None:
            page = self.page(False)
            if page is None:
                return False
        try:
            selector = page.query_selector("#inspector-style")
        except Exception:
            # Expected error:
            # Execution context was destroyed, most likely because of a navigation
            return False
        if selector is not None:
            return True
        return False

    def inject_picker(self, reason: str, page=None) -> bool:
        """
        Ensures that the picker is injected. It's ok to call it multiple times.
        """
        self._check_thread()
        try:
            if self.is_picker_injected(page):
                return True
            if page is None:
                page = self.page(False)
                if page is None:
                    log.debug("page is None in inject_picker!")
                    return False

            self.evaluate_in_all_iframes(page, _load_resource("inspector.js"))
            style_contents = _load_resource("inspector.css")
            self.evaluate_in_all_iframes(
                page,
                'var style = document.getElementById("inspector-style");'
                f"var content = document.createTextNode(`{style_contents}`);"
                "style.appendChild(content);",
            )
            log.debug("Picker code / style injected!")
            self.loop()

            return True
        except Exception:
            log.exception("Error injecting picker.")
            return False

    def evaluate_in_all_iframes(
        self, page: Page, expression: str, inject_frame_data: bool = False
    ) -> None:
        """
        Ensures that the expression is evaluated in the child iFrames if any
        """
        try:
            # we need to wait for the load state before injecting otherwise the evaluation of the picker crashes
            # not finding the body where to inject the picker in
            page.wait_for_load_state()
            page.wait_for_selector("body")
            page.wait_for_timeout(1)

            # retrieving only the first layer of iFrames
            # for additional layers recessiveness is the solution, but doesn't seem necessary right now
            frames = list(page.frames) + list(page.main_frame.child_frames)

            for frame in frames:
                # make sure we wait for the load state to trigger in frames as well
                frame.wait_for_load_state()

                # skipping the detached frames as they are not able to evaluate expressions
                if frame.is_detached():
                    continue

                # returning if page is closed
                if page.is_closed():
                    return

                props = None
                if frame != page.main_frame:
                    props = {}
                    props["name"] = frame.frame_element().get_attribute("name")
                    if props["name"] is None:
                        props["name"] = frame.name
                    props["id"] = frame.frame_element().get_attribute("id")
                    props["cls"] = frame.frame_element().get_attribute("class")
                    props["title"] = frame.frame_element().get_attribute("title")
                    if (props["title"]) is None:
                        props["title"] = frame.title()

                final_exp = (
                    Template(expression).substitute(
                        iFrame=json.dumps(
                            {
                                "name": frame.name,
                                "title": frame.title(),
                                "url": frame.url,
                                "sourceURL": page.url,
                                "isMain": frame == page.main_frame,
                                "props": props,
                            }
                        )
                    )
                    if inject_frame_data
                    else expression
                )

                try:
                    # make sure we wait for the load state to trigger in frames as well
                    frame.wait_for_load_state()
                    frame.wait_for_timeout(1)
                    # inject the code
                    frame.evaluate(final_exp)
                except Exception as e:
                    # when we deal with the main frame, raise exception
                    # the iframes (child frames or attached) can cause unexpected behaviors due to their construction
                    # we can try to address them later
                    if frame == page.main_frame:
                        raise e
                    log.exception(f"Exception occurred inside of an iFrame: {e}")
                    continue

        except Exception as e:
            log.exception(f"Exception occurred evaluating code in iFrames: {e}")
            pass

    def shutdown(self):
        self._looping = False
