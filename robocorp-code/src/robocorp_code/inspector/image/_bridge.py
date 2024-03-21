import json
import os
import subprocess
import sys
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from robocorp_code.inspector.common import (
    STATE_CLOSED,
    STATE_INITIALIZING,
    STATE_PICKING,
)
from robocorp_ls_core.protocols import IEndPoint

DEFAULT_CONFIDENCE = 80


def _base64_to_image(img: str):
    # pylint: disable=import-outside-toplevel
    from .vendor.utils import base64_to_image

    # making sure we remove the unnecessary composition
    img = img.replace("data:image/png;base64,", "")

    return base64_to_image(img)


class ImageBridge:
    """Javascript API bridge for image template locators."""

    def __init__(self, endpoint: Optional[IEndPoint] = None, logger=None) -> None:
        self.endpoint = endpoint

        self.logger = (
            logger if logger is not None else logging.getLogger(self.__class__.__name__)
        )

        self.snipping_process: Optional[subprocess.Popen] = None

    def _launch_snipper(self):
        #: Create the appropriate environment and launch the process
        # - this is blocking and waits for the process to finish
        environ = os.environ.copy()
        environ.pop("PYTHONPATH", "")
        environ.pop("PYTHONHOME", "")
        environ.pop("VIRTUAL_ENV", "")
        environ["PYTHONIOENCODING"] = "utf-8"
        environ["PYTHONUNBUFFERED"] = "1"
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "_snipping_tool.py"),
        ]
        if self.endpoint is not None:
            self.endpoint.notify("$/imageInspectorState", {"state": STATE_PICKING})

        self.snipping_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=environ,
            bufsize=0,
        )
        stdout, _ = self.snipping_process.communicate()

        # If you want to capture the output, you can use stdout.decode('utf-8') to convert it to a string
        output = stdout.decode("utf-8", "replace")

        #: Validating the result from the Snipping Tool
        if not output:
            if self.endpoint is not None:
                self.endpoint.notify("$/imageInspectorState", {"state": STATE_CLOSED})
            raise RuntimeError("Snipping Tool closed abruptly!")

        try:
            result = json.loads(output)
        except ValueError as err:
            if self.endpoint is not None:
                self.endpoint.notify("$/imageInspectorState", {"state": STATE_CLOSED})
            raise RuntimeError(f"Malformed response from picker: {err}") from err

        if "error" in result:
            if self.endpoint is not None:
                self.endpoint.notify("$/imageInspectorState", {"state": STATE_CLOSED})
            raise RuntimeError(result["error"])

        self.logger.debug("Image:: Snapshot taken!")
        if self.endpoint is not None:
            self.endpoint.notify("$/imageInspectorState", {"state": STATE_CLOSED})
        return result

    def pick(self, confidence: Optional[int] = None):
        self.logger.debug("Image:: Starting interactive picker")
        if self.endpoint is not None:
            self.endpoint.notify("$/imageInspectorState", {"state": STATE_INITIALIZING})
        result = self._launch_snipper()

        self.logger.debug("Image:: Snapshot Result:", result)

        return {
            "screenshot": f"data:image/png;base64,{result['screenshot']}",
            "screenResolutionWidth": result["screen_resolution_width"],
            "screenResolutionHeight": result["screen_resolution_height"],
            "screenPixelRatio": result["screen_pixel_ratio"],
            "confidence": confidence,
        }

    def stop(self):
        self.logger.debug("Image:: Stopping interactive picker...")
        if self.snipping_process is not None:
            self.snipping_process.terminate()
            self.snipping_process.kill()
        self.logger.debug("Image:: Process stopped")

    # TODO: replace this implementation when the robocorp library has image recognition
    def validate(
        self,
        image_base64: str,
        confidence: Optional[int] = None,
    ):
        needle = _base64_to_image(image_base64)
        matches = self._find_matches(needle, confidence)

        return len(matches)

    def _find_matches(self, needle, confidence=None):
        self.logger.debug("Image:: Finding matches...")

        import mss  # type: ignore
        import pyscreeze  # type: ignore
        from PIL import Image  # type: ignore

        if confidence is None:
            confidence = DEFAULT_CONFIDENCE

        with mss.mss() as sct:
            monitor = sct.monitors[0]
            screenshot = sct.grab(monitor)
            haystack = Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )

        try:
            self.logger.debug(
                "Image:: Finding template matches (confidence: %s)", confidence
            )
            box = pyscreeze.locate(
                needleImage=needle,
                haystackImage=haystack,
                grayscale=True,
            )
            matches = [] if box is None else [box]
        except Exception as err:
            self.logger.debug(str(err))
            matches = []

        self.logger.debug(
            "Image:: Found %d match%s", len(matches), "" if len(matches) == 1 else "es"
        )

        return matches

    def save_image(self, root_directory: str, image_base64: str) -> str:
        img = _base64_to_image(image_base64)

        images_folder_name = ".images"

        image_name = f"{uuid4()}.png"
        image_root = os.path.join(root_directory, images_folder_name)
        image_path = os.path.join(image_root, image_name)
        self.logger.debug("Image:: Will save to:", image_path)

        try:
            # making sure that the image directory exists
            os.mkdir(image_root)
        except Exception:
            pass

        try:
            self.logger.debug("Image:: Saving IMAGE to file:", image_path)
            img.save(image_path)
        except Exception as e:
            self.logger.debug("Image:: Saving IMAGE to file failed:", e)

        return os.path.join(images_folder_name, image_name)
