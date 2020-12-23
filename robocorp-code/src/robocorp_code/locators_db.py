from robocorp_code.locators.locator_protocols import (
    BrowserLocatorTypedDict,
    ImageLocatorTypedDict,
)
from typing import Optional
import itertools
from functools import partial
from pathlib import Path


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

    def validate(self) -> str:
        """
        :return str:
            Returns an error message or an empty string if everything is ok.
        """
        if not self._locators_database:
            return "The locators.json location to save locators is still not provided."

        return ""

    def _get_next_name_generator(self, pattern):
        next_id = partial(next, itertools.count(0))
        while True:
            yield pattern % (next_id(),)

    def _get_name(self, pattern: str, name: Optional[str] = None):
        if not name:
            db = self._locators_database
            name_generator = self._get_next_name_generator(pattern)
            while True:
                name = next(name_generator)
                if name not in db.locators:
                    return name
        return name

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
        name = self._get_name("Browser.Locator.%02d", name)

        assert name
        # Pass a copy so that the original is not mutated.
        db.locators[name] = Locator.from_dict(browser_locator.copy())
        db.save()
        return name

    def add_image_locator(
        self, image_locator: ImageLocatorTypedDict, name: Optional[str] = None
    ) -> str:
        """
        Adds the image locator with a given name (if a name is not given, one
        is generated).
        :return:
            The name used to add the locator.
        """
        from RPA.core.locators.containers import Locator
        import base64

        images_dir: Path = Path(self._locators_json).parent / ".images"
        images_dir.mkdir(parents=True, exist_ok=True)

        db = self._locators_database
        assert db is not None
        if name:
            path_name = name + "-path.png"
            source_name = name + "-source.png"
        else:
            images = set(x.name for x in images_dir.glob("*.png"))

            name_generator = self._get_next_name_generator("Image.Locator.%02d")
            while True:
                new_name = next(name_generator)
                if new_name in db.locators:
                    continue

                path_name = new_name + "-path.png"
                source_name = new_name + "-source.png"

                if path_name in images:
                    continue
                if source_name in images:
                    continue

                break
            name = new_name

        assert name
        # Convert to the format that's expected.
        path_b64 = image_locator["path_b64"]
        source_b64 = image_locator["source_b64"]

        with (images_dir / path_name).open("wb") as stream:
            stream.write(base64.b64decode(path_b64))

        with (images_dir / source_name).open("wb") as stream:
            stream.write(base64.b64decode(source_b64))

        dct = {
            "type": "image",
            "confidence": image_locator["confidence"],
            "path": ".images/" + path_name,
            "source": ".images/" + source_name,
        }
        db.locators[name] = Locator.from_dict(dct)
        db.save()
        return name
