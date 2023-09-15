import weakref
from typing import List, Tuple

from playwright.sync_api import ElementHandle, Page
from robocorp_ls_core.callbacks import Callback
from robocorp_ls_core.protocols import TypedDict
from robocorp_ls_core.robotframework_log import get_logger

log = get_logger(__name__)


def _load_resource(name):
    from robocorp_code.inspector.web import WEB_RESOURCES_DIR

    inspector_js = WEB_RESOURCES_DIR / name
    return inspector_js.read_text(encoding="utf-8")


# Regular mode (will block until a pick is done).
_PICK_CODE = """
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
_PICK_ASYNC_CODE = """
()=>{
    var callback = (picked)=>{
        console.log('Picked', picked);
        on_picked(picked);
    }
    
    Inspector.startPicker(callback);
}
"""


class LocatorTypedDict(TypedDict):
    strategy: str
    value: str
    matches: int


LocatorNameToLocatorTypedDict = dict


class WebInspector:
    def __init__(self):
        self._page = None
        self._on_picked = Callback()

    def page(self) -> Page:
        page = self._page
        if page is None:
            from robocorp_code.playwright import robocorp_browser

            page = robocorp_browser.page()
            self._page = page

            weak_self = weakref.ref(self)

            def on_picked(*args, **kwargs):
                s = weak_self()
                if s is not None:
                    s._on_picked(*args, **kwargs)

            page.expose_function("on_picked", on_picked)

        return page

    def open(self, url: str) -> Page:
        page = self.page()
        if url:
            page.goto(url)
        return page

    def _query(self, selector):
        page = self.page()
        log.debug("Querying: %s", selector)
        return page.query_selector_all(selector)

    def find_matches(self, strategy, value) -> List[ElementHandle]:
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

    def pick_async(self, on_picked) -> None:
        assert self.is_picker_injected(), "Unable to make pick. Picker not injected."

        page = self.page()

        def call_and_unregister(*args, **kwargs):
            self._on_picked.unregister(on_picked)
            on_picked(*args, **kwargs)

        self._on_picked.register(call_and_unregister)
        page.evaluate(_PICK_ASYNC_CODE)

    def pick(self) -> List[Tuple[str, str]]:
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
        assert self.is_picker_injected(), "Unable to make pick. Picker not injected."

        page = self.page()
        locators = page.evaluate(_PICK_CODE)

        log.debug("Locators found: %s", locators)
        return locators

    def make_full_locators(
        self, locators: List[Tuple[str, str]]
    ) -> LocatorNameToLocatorTypedDict:
        ret: LocatorNameToLocatorTypedDict = {}
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

    def is_picker_injected(self) -> bool:
        page = self.page()
        selector = page.query_selector("#inspector-style")
        if selector is not None:
            return True
        return False

    def inject_picker(self) -> bool:
        try:
            if self.is_picker_injected():
                return True
            page = self.page()

            log.debug("Picker was not injected (injecting now).")
            page.evaluate(_load_resource("inspector.js"))

            style_contents = _load_resource("inspector.css")
            page.evaluate(
                'var style = document.getElementById("inspector-style");'
                f"var content = document.createTextNode(`{style_contents}`);"
                "style.appendChild(content);"
            )
            log.debug("Picker code / style injected!")
            return True
        except Exception:
            log.exception("Error injecting picker.")
            return False
