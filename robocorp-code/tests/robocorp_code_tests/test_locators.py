import pytest
from pathlib import Path


def test_locators_webdriver_basic():
    from robocorp_code.locators.locator_webdriver import Webdriver
    from robocorp_ls_core.robotframework_log import get_logger
    from robocorp_code_tests.fixtures import IMAGE_IN_BASE64

    w = Webdriver(get_logger=get_logger, headless=True)
    w.start()
    w.navigate("http://google.com")

    # i.e.: Uncomment to manually click the element instead of hard-coding
    # value.
    # dct = w.pick_as_browser_locator_dict()
    # print(dct)
    dct = {
        "strategy": "name",
        "value": "q",
        "source": "https://www.google.com/?gws_rd=ssl",
        "screenshot": IMAGE_IN_BASE64,
    }
    assert dct["value"] == "q"
    assert dct["strategy"] == "name"
    result = w.validate_dict_info(dct)
    assert result["matches"] == 1
    w.stop()


@pytest.fixture
def config_options_log(log_file: str):
    from robocorp_code.options import Setup

    prev_log_file = Setup.options.log_file
    prev_verbose = Setup.options.verbose

    Setup.options.log_file = log_file
    Setup.options.verbose = 2

    yield
    Setup.options.log_file = prev_log_file
    Setup.options.verbose = prev_verbose


def test_locators_server(config_options_log):

    from robocorp_code.locators.server.locator_server_manager import (
        LocatorServerManager,
    )
    from robocorp_code.protocols import ActionResultDict

    locator_server_manager = LocatorServerManager()
    browser_locator_start: ActionResultDict = locator_server_manager.browser_locator_start(
        headless=True
    )
    assert browser_locator_start["success"]

    browser_locator_stop: ActionResultDict = locator_server_manager.browser_locator_stop()
    assert browser_locator_stop["success"]


def test_locators_db_browser(tmpdir):
    from robocorp_code.locators_db import LocatorsDB
    import json

    locators_db = LocatorsDB()
    robot_yaml_location = tmpdir.join("robot.yaml")
    locators_db.set_robot_yaml_location(str(robot_yaml_location))
    browser_locator = {
        "strategy": "strategy",
        "value": "value",
        "source": "source",
        "screenshot": "screenshot",
        "type": "browser",
    }
    locators_db.add_browser_locator(browser_locator)
    locators_db.add_browser_locator(browser_locator)

    with open(locators_db.locators_json, "r", encoding="utf-8") as stream:
        assert json.load(stream) == {
            "Browser.Locator.00": {
                "screenshot": "screenshot",
                "source": "source",
                "strategy": "strategy",
                "type": "browser",
                "value": "value",
            },
            "Browser.Locator.01": {
                "screenshot": "screenshot",
                "source": "source",
                "strategy": "strategy",
                "type": "browser",
                "value": "value",
            },
        }


def test_locators_db_images(tmpdir):
    from robocorp_code.locators_db import LocatorsDB
    import json
    from robocorp_code.locators.locator_protocols import ImageLocatorTypedDict
    from robocorp_code_tests.fixtures import IMAGE_IN_BASE64

    locators_db = LocatorsDB()
    robot_yaml_location = tmpdir.join("robot.yaml")
    locators_db.set_robot_yaml_location(str(robot_yaml_location))
    image_locator: ImageLocatorTypedDict = {
        "path_b64": IMAGE_IN_BASE64,
        "source_b64": IMAGE_IN_BASE64,
        "confidence": 80.0,
        "type": "image",
    }
    locators_db.add_image_locator(image_locator)
    locators_db.add_image_locator(image_locator)

    with open(locators_db.locators_json, "r", encoding="utf-8") as stream:

        assert json.load(stream) == {
            "Image.Locator.00": {
                "confidence": 80.0,
                "path": ".images/Image.Locator.00-path.png",
                "source": ".images/Image.Locator.00-source.png",
                "type": "image",
            },
            "Image.Locator.01": {
                "confidence": 80.0,
                "path": ".images/Image.Locator.01-path.png",
                "source": ".images/Image.Locator.01-source.png",
                "type": "image",
            },
        }

    p = Path(str(tmpdir)) / ".images" / "Image.Locator.01-source.png"
    assert p.exists()

    p = Path(str(tmpdir)) / ".images" / "Image.Locator.02-source.png"
    p.write_text("not empty")
    locators_db.add_image_locator(image_locator)

    with open(locators_db.locators_json, "r", encoding="utf-8") as stream:

        assert json.load(stream) == {
            "Image.Locator.00": {
                "confidence": 80.0,
                "path": ".images/Image.Locator.00-path.png",
                "source": ".images/Image.Locator.00-source.png",
                "type": "image",
            },
            "Image.Locator.01": {
                "confidence": 80.0,
                "path": ".images/Image.Locator.01-path.png",
                "source": ".images/Image.Locator.01-source.png",
                "type": "image",
            },
            # i.e.: skip the Image.Locator.02 because the image is there already
            "Image.Locator.03": {
                "confidence": 80.0,
                "path": ".images/Image.Locator.03-path.png",
                "source": ".images/Image.Locator.03-source.png",
                "type": "image",
            },
        }
