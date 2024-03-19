# pylint: disable=too-many-instance-attributes
import base64
import json
import logging
import traceback
from io import BytesIO

import tkinter as tk
from typing import Optional  # type: ignore
import mss  # type: ignore
from PIL import Image  # type: ignore


class ImageSniperToolResult:
    screenshot: Optional[str] = None
    screen_resolution_width: Optional[int] = None
    screen_resolution_height: Optional[int] = None
    screen_pixel_ratio: Optional[int] = None
    error: Optional[str] = None


class SnippingTool:
    def __init__(self, timeout=30):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.timeout = timeout

        #: Final result
        self.error = None
        self.result = ImageSniperToolResult()

        with mss.mss() as sct:
            # NB: Always uses the left-most monitor
            monitor = sct.monitors[1]
            screenshot = sct.grab(monitor)

        #: Display dimensions
        self.screen_width = monitor["width"]
        self.screen_height = monitor["height"]

        self.logger.debug(
            "@@@ Screen dimensions: %dx%d", self.screen_width, self.screen_height
        )
        self.logger.debug("@@@ Screenshot size: %dx%d", *screenshot.size)

        #: Desktop screenshot (as PIL.Image)
        #: create the screenshot before adding anything else on the screen
        # FIXME: there might be a better solution for this as the background might change
        self.screenshot_image = Image.frombytes(
            "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
        )
        #: Desktop screenshot (as PNG bytes)
        self.screenshot_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)

        #: Current snip coordinates
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0

        #: Snipping outline rectangle
        self.rubber_band = None

        # Root widget
        self.root = tk.Tk()

        # Bring window to full screen and top most level. For some reason this
        # overrideredirect toggling is required to make this work on macOS:
        # https://stackoverflow.com/a/42173885/6734941
        try:
            self.root.overrideredirect(True)
            self.root.overrideredirect(False)
            self.root.overrideredirect(True)
        except Exception:  # pylint: disable=broad-except
            self.logger.warning(traceback.format_exc())

        self.root.configure(bg="#7158f1")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.10)
        self.root.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        # Create canvas for drawing content
        self.canvas = tk.Canvas(
            self.root,
            width=self.screen_width,
            height=self.screen_height,
            cursor="crosshair",
            background="#7158f1",
        )
        self.canvas.pack()

        # Focus users input on the canvas
        self.canvas.focus()
        self.canvas.focus_force()

        # Connect the event handlers
        self.canvas.bind("<Escape>", self._on_escape)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)

    def run(self):
        self.logger.debug("@@@ Starting application...")
        # self.root.after(int(self.timeout * 1000), self._on_timeout)
        self.root.mainloop()

        if self.error:
            raise RuntimeError(self.error)

        return self.result

    def quit(self):
        self.root.quit()

    def _to_width(self, value):
        return max(min(value, self.screen_width), 0)

    def _to_height(self, value):
        return max(min(value, self.screen_width), 0)

    def _on_timeout(self, _):
        self.logger.warning("Image:: Timeout reached (%d seconds)", self.timeout)
        self.error = "Timeout reached"
        self.quit()

    def _on_escape(self, _):
        self.logger.warning("Image:: Aborted by user")
        self.error = "Aborted by user"
        self.quit()

    def _on_button_press(self, event):
        self.start_x = self.end_x = self._to_width(event.x)
        self.start_y = self.end_y = self._to_height(event.y)

        if not self.rubber_band:
            self.rubber_band = self.canvas.create_rectangle(
                self.start_x,
                self.start_y,
                self.end_x,
                self.end_y,
                outline="#eebb11",
                fill="#eebb11",
            )

    def _on_move(self, event):
        self.end_x = self._to_width(event.x)
        self.end_y = self._to_height(event.y)

        if self.rubber_band:
            self.canvas.coords(
                self.rubber_band, self.start_x, self.start_y, self.end_x, self.end_y
            )

    def _on_button_release(self, _):
        #: Calculate scale factor - pixel factor
        width, height = self.screenshot_image.size
        width_scale = width / self.root.winfo_width()
        height_scale = height / self.root.winfo_height()

        if width_scale != height_scale:
            # This might mean that the window is not truly fullscreen or
            # that the screenshot missed something
            self.logger.warning(
                "Uneven width/height scaling (%s / %s)", width_scale, height_scale
            )

        scale_factor = height_scale
        self.logger.debug("Image:: Calculated scale factor: %f", scale_factor)

        #: Save dimensions to result
        self.result.screen_resolution_width = self.screen_width
        self.result.screen_resolution_height = self.screen_height
        self.result.screen_pixel_ratio = scale_factor

        #: Calculate coordinates based on the scale_factor
        coordinates = (
            int(scale_factor * min(self.start_x, self.end_x)),
            int(scale_factor * min(self.start_y, self.end_y)),
            int(scale_factor * max(self.start_x, self.end_x)),
            int(scale_factor * max(self.start_y, self.end_y)),
        )

        #: Crop the snipped value from the
        self.logger.debug("Image:: Snip coordinates: %s", coordinates)
        snip = self.screenshot_image.crop(coordinates)

        stream = BytesIO()
        snip.save(stream, format="png")
        snip_bytes = stream.getvalue()

        self.result.screenshot = base64.b64encode(snip_bytes).decode()

        #: Close TK
        self.quit()


def main():
    log_datefmt = "%Y/%m/%d %H:%M:%S"
    log_format = "%(asctime)s.%(msecs)03d › %(levelname)s › %(name)s › %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=log_format, datefmt=log_datefmt)

    # Reduce unwanted debug logging
    logging.getLogger("SnippingTool").setLevel(logging.DEBUG)

    try:
        snipper = SnippingTool()
        result = snipper.run()
    except Exception as err:  # pylint: disable=broad-except
        logging.debug(traceback.format_exc())
        result = ImageSniperToolResult()
        result.error = str(err)

    print(json.dumps(result, default=lambda x: x.__dict__), flush=True)
    return json.dumps(result, default=lambda x: x.__dict__)


if __name__ == "__main__":
    main()
