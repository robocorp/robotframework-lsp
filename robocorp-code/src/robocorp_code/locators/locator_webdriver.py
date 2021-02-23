import platform
from typing import Optional, Tuple, Any, Dict

from RPA.core import webdriver
import pkg_resources
from selenium.common.exceptions import (
    InvalidSessionIdException,
    JavascriptException,
    NoSuchWindowException,
    TimeoutException,
    WebDriverException,
)
import logging
from robocorp_code.locators.locator_protocols import (
    BrowserLocatorTypedDict,
    BrowserLocatorValidationTypedDict,
)


def load_resource(filename):
    with pkg_resources.resource_stream(__name__, filename) as fd:
        return fd.read().decode("utf-8")


class WebdriverError(Exception):
    """Common exception for all webdriver errors."""


class Webdriver:
    SCRIPT_TIMEOUT = 30.0  # seconds

    def __init__(self, *, get_logger=logging.getLogger, headless=False):
        """
        :param logger:
            The logger to be used. If not specified the standard logging is used.
            
        :param headless:
            If True the browser will start in headless mode (only supported
            for Chrome right now).
        """
        # XXX: get logger as parameter
        # XXX: accept headless to test in CI
        logger = get_logger(__name__)
        webdriver.LOGGER = get_logger(webdriver.__name__)
        self._headless = headless

        self.logger = logger
        self._driver = None
        self._snippets: Dict[str, str] = {
            "simmer": load_resource("./resources/simmer.js"),
            "style": load_resource("./resources/style.js"),
            "picker": load_resource("./resources/picker.js"),
        }

    def _inject_requirements(self) -> None:
        if not self._driver.find_elements_by_css_selector(
            'style[data-name="robocode"]'
        ):
            self._driver.execute_script(self._snippets["simmer"])
            self._driver.execute_script(self._snippets["style"])

    def _execute_func(self, func, *args, **kwargs):
        def error(msg):
            self.logger.warning(msg)
            raise WebdriverError(msg)

        if not self._driver:
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
            self._driver = None
            error(exc)
        except Exception as exc:
            self._driver = None
            raise

    @property
    def is_running(self):
        try:
            if self._driver:
                # Mock interaction to check if webdriver is still available
                _ = self._driver.title
                return True
        except (InvalidSessionIdException, WebDriverException, NoSuchWindowException):
            self._driver = None
        return False

    @property
    def title(self) -> str:
        return self._driver.title

    @property
    def url(self) -> str:
        return self._driver.current_url

    def start(self):
        self.logger.info("Starting browser")
        self._driver, browser = self._create_driver()

        self.logger.info("Started webdriver for %s", browser)
        self._driver.set_script_timeout(self.SCRIPT_TIMEOUT)

    def _create_driver(self):
        browsers = webdriver.DRIVER_PREFERENCE[platform.system()]
        for browser in browsers:
            kwargs = {}
            if self._headless:
                from selenium.webdriver import ChromeOptions

                chrome_options = ChromeOptions()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--window-size=1280,1024")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.headless = True

                kwargs["options"] = chrome_options
            for download in [False, True]:
                if hasattr(webdriver, "executable"):  # old version
                    executable = webdriver.executable(browser, download=download)
                else:
                    # new version
                    if not download:
                        executable = webdriver.cache(browser)
                        if not executable:
                            continue
                    else:
                        executable = webdriver.download(browser)
                try:
                    if executable:
                        driver = webdriver.start(
                            browser, executable_path=executable, **kwargs
                        )
                    else:
                        driver = webdriver.start(browser, **kwargs)
                    return driver, browser
                except WebDriverException:
                    if self.logger.level >= logging.DEBUG:
                        self.logger.exception(
                            "Error trying to start with executable: %s", executable
                        )

        raise ValueError("No valid browser found")

    def stop(self):
        if self._driver:
            self.logger.info("Stopping browser")
            # XXX: changed to '_driver.quit()'.
            self._driver.quit()
            self._driver = None

    def navigate(self, url):
        self._driver.get(url)

    def pick(self) -> Tuple[Optional[Any], Optional[str], Optional[str]]:
        def pick():
            selector = self._driver.execute_async_script(self._snippets["picker"])

            if not selector:
                return None, None, None

            element = self._driver.find_element_by_css_selector(selector)

            finders = (
                ("id", self._driver.find_elements_by_id),
                ("name", self._driver.find_elements_by_name),
                ("link", self._driver.find_elements_by_link_text),
                ("class", self._driver.find_elements_by_class_name),
                ("tag", self._driver.find_elements_by_tag_name),
            )

            for attribute_name, finder in finders:
                attribute = element.get_attribute(attribute_name)
                if attribute:
                    matches = finder(attribute)
                    if len(matches) == 1 and matches[0] == element:
                        return element, attribute_name, attribute

            return element, "css", selector

        self.logger.info("Starting interactive picker")
        return self._execute_func(pick)

    def find(self, strategy, value):
        def find():
            finder = {
                "id": self._driver.find_elements_by_id,
                "name": self._driver.find_elements_by_name,
                "link": self._driver.find_elements_by_link_text,
                "class": self._driver.find_elements_by_class_name,
                "tag": self._driver.find_elements_by_tag_name,
                "xpath": self._driver.find_elements_by_xpath,
                "css": self._driver.find_elements_by_css_selector,
            }.get(strategy)

            if not finder:
                raise ValueError(f"Unknown search strategy: {strategy}")

            return finder(value)

        self.logger.info("Finding elements where %s = %s", strategy, value)
        return self._execute_func(find)

    def highlight(self, elements):
        def highlight():
            script = "".join(
                f'arguments[{idx}].setAttribute("data-robocode-highlight", "");'
                for idx in range(len(elements))
            )
            self._driver.execute_script(script, *elements)

        self.logger.info("Highlighting %s elements", len(elements))
        return self._execute_func(highlight)

    def clear(self):
        def clear():
            elements = self._driver.find_elements_by_css_selector(
                "[data-robocode-highlight]"
            )
            script = "".join(
                f'arguments[{idx}].removeAttribute("data-robocode-highlight");'
                for idx in range(len(elements))
            )
            self._driver.execute_script(script, *elements)

        self.logger.info("Clearing highlights")
        return self._execute_func(clear)

    def pick_as_browser_locator_dict(self) -> BrowserLocatorTypedDict:
        # XXX: LocateHandler
        if not self.is_running:
            raise WebdriverError("No active browser session")

        self.clear()
        element, strategy, value = self.pick()

        if not element or not strategy or not value:
            raise WebdriverError("Failed to identify locator")

        screenshot: str = element.screenshot_as_base64
        response: BrowserLocatorTypedDict = {
            "strategy": strategy,
            "value": value,
            "source": self.url,
            "screenshot": screenshot,
            "type": "browser",
        }

        return response

    def validate_dict_info(
        self, data: BrowserLocatorTypedDict
    ) -> BrowserLocatorValidationTypedDict:
        # XXX: ValidateHandler
        if not self.is_running:
            raise WebdriverError("No active browser session")

        strategy = data.get("strategy")
        value = data.get("value")
        if not strategy or not value:
            raise WebdriverError("Missing required fields from request")

        self.clear()
        matches = self.find(strategy, value)

        if matches:
            self.highlight(matches)

        if len(matches) == 1:
            screenshot = matches[0].screenshot_as_base64
        else:
            screenshot = ""

        response: BrowserLocatorValidationTypedDict = {
            "matches": len(matches),
            "source": self.url,
            "screenshot": screenshot,
        }

        return response


if __name__ == "__main__":
    w = Webdriver()
    w.start()
    w.navigate("http://google.com")
    dct = w.pick_as_browser_locator_dict()
    assert dct
    w.validate_dict_info(dct)
    w.stop()
