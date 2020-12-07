from pathlib import Path
import platform

from RPA.core import webdriver
import pkg_resources
from selenium.common.exceptions import (
    InvalidSelectorException,
    InvalidSessionIdException,
    JavascriptException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)

from robocorp_ls_core.robotframework_log import get_logger
from robocorp_code.protocols import ActionResult


log = get_logger(__name__)


def load_resource(filename):
    path = str(Path(filename))
    with pkg_resources.resource_stream(__name__, path) as fd:
        return fd.read().decode("utf-8")


class WebdriverError(Exception):
    """Common exception for all webdriver errors."""


class Webdriver:
    SCRIPT_TIMEOUT = 30.0  # seconds

    def __init__(self):
        self.driver = None
        self.snippets = {}
        self._load_snippets()

    def _load_snippets(self):
        self.snippets = {
            "simmer": load_resource("simmer.js"),
            "style": load_resource("style.js"),
            "picker": load_resource("picker.js"),
        }

    def _inject_requirements(self):
        if not self.driver.find_elements_by_css_selector('style[data-name="robocode"]'):
            self.driver.execute_script(self.snippets["simmer"])
            self.driver.execute_script(self.snippets["style"])

    def _execute_func(self, func, *args, **kwargs):
        def error(msg):
            log.warning(msg)
            raise WebdriverError(msg)

        if not self.driver:
            error("No available webdriver")

        try:
            self._inject_requirements()
            return func(*args, **kwargs)
        except TimeoutException:
            error("Timeout while running script")
        except JavascriptException as exc:
            error("Error while running script: {}".format(exc))
        except WebdriverError as exc:
            error("Webdriver error: {}".format(exc))
        except (InvalidSessionIdException, NoSuchWindowException) as exc:
            self.driver = None
            error(exc)
        except Exception as exc:
            self.driver = None
            raise

    @property
    def is_running(self):
        try:
            if self.driver:
                # Mock interaction to check if webdriver is still available
                _ = self.driver.title
                return True
        except (InvalidSessionIdException, WebDriverException, NoSuchWindowException):
            self.driver = None
        return False

    @property
    def title(self):
        return self.driver.title

    @property
    def url(self):
        return self.driver.current_url

    def start(self):
        log.info("Starting browser")
        self.driver, browser = self._create_driver()

        log.info("Started webdriver for %s", browser)
        self.driver.set_script_timeout(self.SCRIPT_TIMEOUT)

    def _create_driver(self):
        browsers = webdriver.DRIVER_PREFERENCE[platform.system()]
        for browser in browsers:
            for download in [False, True]:
                executable = webdriver.executable(browser, download=download)
                try:
                    if executable:
                        driver = webdriver.start(browser, executable_path=executable)
                    else:
                        driver = webdriver.start(browser)
                    return driver, browser
                except WebDriverException:
                    pass

        raise ValueError("No valid browser found")

    def stop(self):
        if self.driver:
            log.info("Stopping browser")
            try:
                # XXX: changed to 'driver.quit()'.
                self.driver.quit()
            except AttributeError:
                self.driver.stop()
            self.driver = None

    def navigate(self, url):
        self.driver.get(url)

    def pick(self):
        def pick():
            selector = self.driver.execute_async_script(self.snippets["picker"])

            if not selector:
                return None, None, None

            element = self.driver.find_element_by_css_selector(selector)

            finders = (
                ("id", self.driver.find_elements_by_id),
                ("name", self.driver.find_elements_by_name),
                ("link", self.driver.find_elements_by_link_text),
                ("class", self.driver.find_elements_by_class_name),
                ("tag", self.driver.find_elements_by_tag_name),
            )

            for attribute_name, finder in finders:
                attribute = element.get_attribute(attribute_name)
                if attribute:
                    matches = finder(attribute)
                    if len(matches) == 1 and matches[0] == element:
                        return element, attribute_name, attribute

            return element, "css", selector

        log.info("Starting interactive picker")
        return self._execute_func(pick)

    def find(self, strategy, value):
        def find():
            finder = {
                "id": self.driver.find_elements_by_id,
                "name": self.driver.find_elements_by_name,
                "link": self.driver.find_elements_by_link_text,
                "class": self.driver.find_elements_by_class_name,
                "tag": self.driver.find_elements_by_tag_name,
                "xpath": self.driver.find_elements_by_xpath,
                "css": self.driver.find_elements_by_css_selector,
            }.get(strategy)

            if not finder:
                raise ValueError(f"Unknown search strategy: {strategy}")

            return finder(value)

        log.info("Finding elements where %s = %s", strategy, value)
        return self._execute_func(find)

    def highlight(self, elements):
        def highlight():
            script = "".join(
                f'arguments[{idx}].setAttribute("data-robocode-highlight", "");'
                for idx in range(len(elements))
            )
            self.driver.execute_script(script, *elements)

        log.info("Highlighting %s elements", len(elements))
        return self._execute_func(highlight)

    def clear(self):
        def clear():
            elements = self.driver.find_elements_by_css_selector(
                "[data-robocode-highlight]"
            )
            script = "".join(
                f'arguments[{idx}].removeAttribute("data-robocode-highlight");'
                for idx in range(len(elements))
            )
            self.driver.execute_script(script, *elements)

        log.info("Clearing highlights")
        return self._execute_func(clear)

    def pick_as_dict_info(self) -> ActionResult[dict]:
        # XXX: LocateHandler
        if not self.is_running:
            return ActionResult(True, "No active browser session", None)

        self.clear()
        element, strategy, value = self.pick()

        if not element or not strategy or not value:
            return ActionResult(False, "Failed to identify locator", None)

        response = {
            "strategy": strategy,
            "value": value,
            "source": self.url,
            "screenshot": element.screenshot_as_base64,
        }

        return ActionResult(True, None, response)

    def validate_dict_info(self, data: dict) -> ActionResult:
        # XXX: ValidateHandler
        if not self.is_running:
            return ActionResult(False, "No active browser session", None)

        strategy = data.get("strategy")
        value = data.get("value")
        if not strategy or not value:
            return ActionResult(False, "Missing required fields from request", None)

        try:
            self.clear()
            matches = self.find(strategy, value)

            if matches:
                self.highlight(matches)

            if len(matches) == 1:
                screenshot = matches[0].screenshot_as_base64
            else:
                screenshot = ""

            response = {
                "matches": len(matches),
                "source": self.url,
                "screenshot": screenshot,
            }

            return ActionResult(True, None, response)
        except Exception as err:
            return ActionResult(False, str(err), None)


if __name__ == "__main__":
    w = Webdriver()
    w.start()
    w.navigate("http://google.com")
    action_result = w.pick_as_dict_info()
    assert action_result.result
    w.validate_dict_info(action_result.result)
    w.stop()
