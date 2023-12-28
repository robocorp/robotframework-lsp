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

log = get_logger(__name__)


STATE_BROWSER_INITIALIZING = "browserInitializing"
STATE_BROWSER_OPENED = "browserOpened"
STATE_BROWSER_CLOSED = "browserClosed"
STATE_BROWSER_PICKING = "browserPicking"
STATE_BROWSER_NOT_PICKING = "browserNotPicking"


def _load_resource(name):
    from robocorp_code.inspector.web import WEB_RESOURCES_DIR

    inspector_js = WEB_RESOURCES_DIR / name
    return inspector_js.read_text(encoding="utf-8")


# Regular mode (will block until a pick is done).
_SYNC_SINGLE_PICK_CODE = """
()=>{
    var promise = new Promise((resolve, reject) => {
        var callback = (picked)=>{
            // console.log('Picked', picked);
            resolve(picked);
        }
        Inspector.startPicker(callback);
    });

    return promise;
}
"""

# Async mode (will start a pick and when the pick is
# done an event will be sent).
# It'll keep picking until cancelled.
_ASYNC_MULTI_PICK_CODE = """
()=>{
    var callback = (picked)=>{
        // console.log('Picked', picked);
        on_picked(picked);
    }

    var nonStopRun = true;
    Inspector.startPicker(callback, nonStopRun);
}
"""
_ASYNC_MULTI_PICK_IFRAME_CODE = """
()=>{
    var callback = (picked)=>{
        // console.log('Picked', picked);
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
    def __init__(self, endpoint: Optional[IEndPoint] = None) -> None:
        """
        Args:
            endpoint: If given notifications on the state will be given.
        """
        self._page: Optional[Page] = None
        self._on_picked = Callback()
        self._current_thread = threading.current_thread()
        self._picking = False
        self._pick_async_code_evaluate_worked = False
        self._looping = False
        self._last_picker_check: int = 0
        self._endpoint = endpoint

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

    def close_browser(self):
        self._check_thread()
        page = self._page
        if page is not None and not page.is_closed():
            page.close()

    def page(self, auto_create) -> Optional[Page]:
        self._check_thread()

        self.loop()

        page = self._page
        if page is None or page.is_closed():
            if not auto_create:
                return None

            endpoint = self._endpoint
            if endpoint is not None:
                endpoint.notify(
                    "$/webInspectorState", {"state": STATE_BROWSER_INITIALIZING}
                )

            from robocorp_code.playwright import robocorp_browser

            log.debug(f"Page is None or Closed. Creating a new one...")
            page = robocorp_browser.page()
            self._page = page

            if endpoint is not None:
                endpoint.notify("$/webInspectorState", {"state": STATE_BROWSER_OPENED})

            weak_self = weakref.ref(self)

            def mark_closed(*args, **kwargs):
                log.debug(f"Mark page closed")
                s = weak_self()
                if s is not None:
                    s._page = None
                    self._picking = False
                    self._pick_async_code_evaluate_worked = False

                if endpoint is not None:
                    endpoint.notify(
                        "$/webInspectorState", {"state": STATE_BROWSER_CLOSED}
                    )

            page.on("close", mark_closed)
            page.on("crash", mark_closed)

            def on_picked(*args, **kwargs):
                log.info(f"## Picked item: {args}")
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

    def _query(self, selector):
        self._check_thread()
        page = self.page(False)
        if page is None:
            return []
        log.debug("Querying: %s", selector)
        return page.query_selector_all(selector)

    def find_matches(self, strategy, value) -> List[ElementHandle]:
        self._check_thread()
        if strategy == "id":
            found_matches = self._query(f"#{value}")
            return found_matches
        elif strategy == "css":
            found_matches = self._query(value)
            return found_matches
        elif strategy == "xpath":
            found_matches = self._query(f"xpath={value}")
            return found_matches
        elif strategy == "link":
            found_matches = self._query(f"a:has-text({value!r})")
            return found_matches
        elif strategy == "name":
            found_matches = self._query(f"[name={value!r}]")
            return found_matches
        else:
            raise ValueError(f"Unexpected strategy: {strategy} (value: {value}).")

        # Note: these 2 were referenced in the selenium version but I (fabioz)
        # didn't find how the picker would generate these, so, keeping those
        # out for now.
        # "class": By.CLASS_NAME,
        # "tag": By.TAG_NAME,

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
            endpoint.notify("$/webInspectorState", {"state": STATE_BROWSER_PICKING})

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
                            page, _ASYNC_MULTI_PICK_IFRAME_CODE, inject_frame_data=True
                        )
                        self._pick_async_code_evaluate_worked = True
                    except Exception:
                        log.exception("Error enabling async pick mode.")
                return True

            if not self.inject_picker(reason):
                return False

            try:
                self.evaluate_in_all_iframes(
                    page, _ASYNC_MULTI_PICK_IFRAME_CODE, inject_frame_data=True
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

        endpoint = self._endpoint
        if endpoint is not None:
            endpoint.notify("$/webInspectorState", {"state": STATE_BROWSER_NOT_PICKING})

        page = self.page(False)
        if page is not None:
            try:
                page.evaluate(_ASYNC_CANCEL_PICK_CODE)
            except Exception:
                log.exception("Error evaluating cancel pick code.")

    def pick(self) -> Optional[List[Tuple[str, str]]]:
        """
        Waits for the user to pick something in the page. When the user does the
        pick (or cancels it), returns a list of tuples with `name[:<optional_strategy>], value`
        which may be used to match the picked element.

        Return example:
            [
                ["css", ".step:nth-child(3) > .icon"],
                ["xpath:position", "//div[3]/div"]
            ]
        """
        self._check_thread()
        if not self.inject_picker("pick (sync)"):
            raise RuntimeError(
                "Unable to make pick. It was not possible to inject the picker code."
            )

        page = self.page(False)
        if page is None:
            return None
        try:
            locators = page.evaluate(_SYNC_SINGLE_PICK_CODE)
        except Exception:
            log.exception(
                "While (sync) picking an exception happened (most likely the user changed the url or closed the browser)."
            )
            return None

        log.debug("Locators found: %s", locators)
        return locators

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

            # we need to wait for the load state before injecting otherwise the evaluation of the picker crashes
            # not finding the body where to inject the picker in
            page.wait_for_load_state()

            self.evaluate_in_all_iframes(page, _load_resource("inspector.js"))
            style_contents = _load_resource("inspector.css")
            self.evaluate_in_all_iframes(
                page,
                'var style = document.getElementById("inspector-style");'
                f"var content = document.createTextNode(`{style_contents}`);"
                "style.appendChild(content);",
            )

            self.loop()

            return True
        except Exception:
            log.exception("Error injecting picker.")
            return False

    def evaluate_in_all_iframes(
        self, page: Page, expression: str, inject_frame_data: bool = False
    ) -> None:
        # retrieving only the first layer of iFrames
        # for additional layers recessiveness is the solution, but doesn't seem necessary right now
        frames = list(page.frames) + list(page.main_frame.child_frames)

        for frame in frames:
            # skipping the detached frames as they are not able to evaluate expressions
            if frame.is_detached():
                continue
            log.info(f">>> Injecting in: {frame}")

            props = None
            if frame != page.main_frame:
                props = {}
                props["name"] = frame.frame_element().get_attribute("name")
                props["id"] = frame.frame_element().get_attribute("id")
                props["cls"] = frame.frame_element().get_attribute("class")
                props["title"] = frame.frame_element().get_attribute("title")

            final_exp = (
                Template(expression).substitute(
                    iFrame=json.dumps(
                        {
                            "name": frame.name,
                            "title": frame.title(),
                            "url": frame.url,
                            "isMain": frame == page.main_frame,
                            "props": props,
                        }
                    )
                )
                if inject_frame_data
                else expression
            )
            frame.evaluate(final_exp)
