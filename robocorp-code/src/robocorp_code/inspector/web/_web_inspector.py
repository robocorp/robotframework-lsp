import threading
import time
import weakref
from typing import List, Optional, Tuple

from playwright.sync_api import ElementHandle
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core.protocols import TypedDict
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


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
        var singlePick = true;
        Inspector.startPicker(callback, singlePick);
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
    
    var singlePick = false;
    Inspector.startPicker(callback, singlePick);
}
"""

_ASYNC_CANCEL_PICK_CODE = """
()=>{
    Inspector.cancelPick();
}
"""


class LocatorTypedDict(TypedDict):
    strategy: str
    value: str
    matches: int


LocatorNameToLocatorTypedDict = dict


class WebInspector:
    def __init__(self) -> None:
        self._page: Optional[Page] = None
        self._on_picked = Callback()
        self._current_thread = threading.current_thread()
        self._picking = False
        self._looping = False
        self._last_picker_check: int = 0

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
                                if not self.is_picker_injected(page):
                                    if self.inject_picker("loop", page):
                                        page.evaluate(_ASYNC_MULTI_PICK_CODE)
                except PlaywrightError:
                    # If the page is closed while we're looping we may get an exception
                    # (don't let it out).
                    self._page = None
        finally:
            self._looping = False

    def close_browser(self):
        self._check_thread()
        page = self._page
        if page is not None and not page.is_closed():
            page.close()

    def page(self) -> Optional[Page]:
        self._check_thread()

        self.loop()

        page = self._page
        if page is None or page.is_closed():
            from robocorp_code.playwright import robocorp_browser

            page = robocorp_browser.page()
            self._page = page

            weak_self = weakref.ref(self)

            def on_picked(*args, **kwargs):
                s = weak_self()
                if s is not None:
                    s._on_picked(*args, **kwargs)

            try:
                page.expose_function("on_picked", on_picked)
            except PlaywrightError:
                self._page = None
                return None

            def mark_closed(*args, **kwargs):
                s = weak_self()
                if s is not None:
                    s._page = None

            page.on("close", mark_closed)
            page.on("crash", mark_closed)

        return page

    def start_log_console(self):
        """
        Can be used to show all the console messages being received from the browser.
        """
        page = self.page()

        def dbg(*args):
            log.debug(*[str(x) for x in args])

        page.on("console", dbg)

    def open(self, url: str) -> Optional[Page]:
        self._check_thread()
        self.loop()

        page = self.page()
        if page is None:
            return None
        if url:
            page.goto(url)

        return page

    def open_if_new(self, url_if_new):
        self._check_thread()

        self.loop()

        page = self._page
        if page is None or page.is_closed():
            self.open(url_if_new)

    def _query(self, selector):
        self._check_thread()
        page = self.page()
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

    def pick_async(self, on_picked) -> bool:
        """
        Starts the picker and calls `on_picked(locators)` afterwards.

        Returns:
            True if the given function was registered as the picker function
            and False otherwise.

        Note: the `locators` may be None if the user makes some navigation.

        Note: if already picking this will not do anything (only one picker
              callback can be registered at a time).
        """
        self._check_thread()
        self._picking = True
        assert self.inject_picker(
            "pick_async"
        ), "Unable to make pick. Picker not injected."

        page = self.page()
        if page is None:
            return False

        if len(self._on_picked) == 0:
            self._on_picked.register(on_picked)
            page.evaluate(_ASYNC_MULTI_PICK_CODE)
            return True
        return False

    def stop_pick_async(self):
        self._picking = False
        self._check_thread()

        self._on_picked.clear()

        page = self.page()
        page.evaluate(_ASYNC_CANCEL_PICK_CODE)

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
        assert self.inject_picker(
            "pick (sync)"
        ), "Unable to make pick. Picker not injected."

        page = self.page()
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

    def make_full_locators(
        self, locators: Optional[List[Tuple[str, str]]]
    ) -> LocatorNameToLocatorTypedDict:
        self._check_thread()
        ret: LocatorNameToLocatorTypedDict = {}
        if not locators:
            return ret
        for name, value in locators:
            log.debug("Making full locator for: name[%s] value[%s]", name, value)
            strategy = name.split(":", 1)[0]

            matches = self.find_matches(strategy, value)
            if matches and len(matches) == 1:
                loc: LocatorTypedDict = {
                    "strategy": str(strategy),
                    "value": str(value),
                    "matches": len(matches),
                }
                ret[str(name)] = loc

        return ret

    def is_picker_injected(self, page=None) -> bool:
        self._check_thread()
        if page is None:
            page = self.page()
            if page is None:
                return False
        selector = page.query_selector("#inspector-style")
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
                page = self.page()
                if page is None:
                    return False

            log.debug(f"Picker was not injected (injecting now. Reason: {reason}).")
            page.evaluate(_load_resource("inspector.js"))

            style_contents = _load_resource("inspector.css")
            page.evaluate(
                'var style = document.getElementById("inspector-style");'
                f"var content = document.createTextNode(`{style_contents}`);"
                "style.appendChild(content);"
            )
            log.debug("Picker code / style injected!")
            self.loop()

            return True
        except Exception:
            log.exception("Error injecting picker.")
            return False
