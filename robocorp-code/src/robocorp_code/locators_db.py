from robocorp_code.locators.locator_protocols import BrowserLocatorTypedDict
from typing import Optional
import itertools
from functools import partial


class LocatorsDB(object):
    def __init__(self):
        self._locators_database = None
        self._locators_json = None

    def set_robot_yaml_location(self, robot_yaml_location: str):
        if not robot_yaml_location:
            self._locators_database = None
            self._locators_json = None
            return

        from RPA.core.locators.database import LocatorsDatabase
        from pathlib import Path

        path = Path(robot_yaml_location)

        # The locators.json is along the robot.yaml
        locators_json = str(path.parent / "locators.json")
        self._locators_json = locators_json

        self._locators_database = LocatorsDatabase(locators_json)
        self._locators_database.load()
        self._next_id = partial(next, itertools.count(0))

    @property
    def locators_json(self):
        return self._locators_json

    def _next_name(self):
        return "Browser.Locator.%02d" % (self._next_id(),)

    def validate(self) -> str:
        """
        :return str:
            Returns an error message or an empty string if everything is ok.
        """
        if not self._locators_database:
            return "The locators.json location to save locators is still not provided."

        return ""

    def add_browser_locator(
        self, browser_locator: BrowserLocatorTypedDict, name: Optional[str] = None
    ) -> str:
        """
        Adds the browser locator with a given name (if a name is not given, one
        is generated).
        :return:
            The name used to add the locator.
        """
        from RPA.core.locators.containers import Locator

        db = self._locators_database
        assert db is not None

        if not name:
            while True:
                name = self._next_name()
                if name not in db.locators:
                    break

        assert name
        # Pass a copy so that the original is not mutated.
        db.locators[name] = Locator.from_dict(browser_locator.copy())
        db.save()
        return name
