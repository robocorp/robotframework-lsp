import pytest


def test_locators_webdriver_basic():
    from robocorp_code.locators.locator_webdriver import Webdriver
    from robocorp_ls_core.robotframework_log import get_logger

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
        "screenshot": "iVBORw0KGgoAAAANSUhEUgAAAb8AAAAiCAYAAADPnNdbAAAAAXNSR0IArs4c6QAAAJ1JREFUeJzt1TEBACAMwDDAv+fhAo4mCvp1z8wsAAg5vwMA4DXzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgBzzAyDH/ADIMT8AcswPgJwLXQ0EQMJRx4AAAAAASUVORK5CYII=",
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


def test_locators_db(tmpdir):
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
